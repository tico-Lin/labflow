"""
檔案分類 API 路由

提供檔案自動分類、批量分類、分類結果查詢等功能。

端點：
- POST /files/classify - 批量分類檔案
- POST /files/{file_id}/auto-classify - 自動分類單個檔案
- GET /files/classifications - 查詢分類統計
- GET /files/{file_id}/classification - 查詢檔案的分類結果

作者：GitHub Copilot
創建日期：2026-02-17
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import get_current_user_optional, is_offline_user
from ..services.classification_service import FileClassificationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["File Classification"])

# 初始化分類服務
classification_service = FileClassificationService()


@router.post(
    "/classify",
    response_model=schemas.BatchClassificationResponse,
    summary="批量分類檔案",
    description="""
    批量自動分類檔案並可選擇自動添加標籤。

    功能：
    - 根據檔名和擴展名識別檔案類型
    - 提取元數據（樣品名、日期、儀器類型等）
    - 生成標籤建議
    - 可自動創建和添加標籤

    權限：需要 Editor 或 Admin 角色
    """,
)
def batch_classify_files(
    request: schemas.BatchClassificationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_optional),
):
    """批量分類檔案"""
    # 檢查離線模式
    if is_offline_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="離線模式下不允許執行批量分類。請登錄後執行此操作。",
        )
    # 檢查權限（需要 editor 或 admin）
    if current_user.get("role") not in ["editor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有 Editor 或 Admin 可以執行批量分類",
        )

    results = []
    errors = []
    successful = 0
    failed = 0

    for file_id in request.file_ids:
        try:
            # 查詢檔案
            db_file = db.query(models.File).filter(models.File.id == file_id).first()
            if not db_file:
                errors.append({"file_id": file_id, "error": f"檔案不存在: {file_id}"})
                failed += 1
                continue

            # 執行分類
            classification_result = classification_service.classify_file(
                db_file.filename
            )

            tags_created = []
            tags_added = []

            # 自動添加標籤
            if request.auto_tag and classification_result.suggested_tags:
                for tag_name in classification_result.suggested_tags:
                    # 查找或創建標籤
                    tag = (
                        db.query(models.Tag).filter(models.Tag.name == tag_name).first()
                    )

                    if not tag:
                        if request.auto_create_tags:
                            # 創建新標籤
                            tag = models.Tag(name=tag_name)
                            db.add(tag)
                            db.flush()  # 獲取 tag.id
                            tags_created.append(tag_name)
                            logger.info(f"自動創建標籤: {tag_name}")
                        else:
                            # 不自動創建，跳過
                            continue

                    # 添加標籤關聯（避免重複）
                    if tag not in db_file.tags:
                        db_file.tags.append(tag)
                        tags_added.append(tag_name)

            # 保存分類結果到註解
            classification_annotation = models.Annotation(
                file_id=db_file.id,
                data={
                    "classification": {
                        "file_type": classification_result.file_type,
                        "confidence": classification_result.confidence,
                        "metadata": classification_result.metadata,
                        "suggested_tags": classification_result.suggested_tags,
                    }
                },
                source="auto",
            )
            db.add(classification_annotation)

            db.commit()

            # 添加到結果
            results.append(
                schemas.FileClassificationResponse(
                    file_id=db_file.id,
                    filename=db_file.filename,
                    classification=schemas.ClassificationResult(
                        file_type=classification_result.file_type,
                        confidence=classification_result.confidence,
                        suggested_tags=classification_result.suggested_tags,
                        metadata=classification_result.metadata,
                        source=classification_result.source,
                    ),
                    tags_created=tags_created,
                    tags_added=tags_added,
                )
            )

            successful += 1
            logger.info(f"檔案分類成功: {db_file.filename} (ID: {file_id})")

        except Exception as e:
            db.rollback()
            logger.error(f"分類檔案失敗 (ID: {file_id}): {str(e)}")
            errors.append({"file_id": file_id, "error": str(e)})
            failed += 1

    return schemas.BatchClassificationResponse(
        total=len(request.file_ids),
        successful=successful,
        failed=failed,
        results=results,
        errors=errors,
    )


@router.post(
    "/{file_id}/auto-classify",
    response_model=schemas.FileClassificationResponse,
    summary="自動分類單個檔案",
    description="""
    自動分類指定檔案並返回分類結果。

    可選擇是否自動添加建議的標籤。

    權限：需要 Editor 或 Admin 角色
    """,
)
def auto_classify_file(
    file_id: int,
    auto_tag: bool = True,
    auto_create_tags: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_optional),
):
    """自動分類單個檔案"""
    # 檢查離線模式
    if is_offline_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="離線模式下不允許執行檔案分類。請登錄後執行此操作。",
        )
    # 檢查權限
    if current_user.get("role") not in ["editor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有 Editor 或 Admin 可以執行檔案分類",
        )

    # 查詢檔案
    db_file = db.query(models.File).filter(models.File.id == file_id).first()
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"檔案不存在: {file_id}"
        )

    try:
        # 執行分類
        classification_result = classification_service.classify_file(db_file.filename)

        tags_created = []
        tags_added = []

        # 自動添加標籤
        if auto_tag and classification_result.suggested_tags:
            for tag_name in classification_result.suggested_tags:
                # 查找或創建標籤
                tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()

                if not tag:
                    if auto_create_tags:
                        # 創建新標籤
                        tag = models.Tag(name=tag_name)
                        db.add(tag)
                        db.flush()
                        tags_created.append(tag_name)
                        logger.info(f"自動創建標籤: {tag_name}")
                    else:
                        continue

                # 添加標籤關聯（避免重複）
                if tag not in db_file.tags:
                    db_file.tags.append(tag)
                    tags_added.append(tag_name)

        # 保存分類結果到註解
        classification_annotation = models.Annotation(
            file_id=db_file.id,
            data={
                "classification": {
                    "file_type": classification_result.file_type,
                    "confidence": classification_result.confidence,
                    "metadata": classification_result.metadata,
                    "suggested_tags": classification_result.suggested_tags,
                }
            },
            source="auto",
        )
        db.add(classification_annotation)

        db.commit()

        logger.info(
            f"檔案分類成功: {db_file.filename} -> {classification_result.file_type} "
            f"(confidence: {classification_result.confidence:.2f})"
        )

        return schemas.FileClassificationResponse(
            file_id=db_file.id,
            filename=db_file.filename,
            classification=schemas.ClassificationResult(
                file_type=classification_result.file_type,
                confidence=classification_result.confidence,
                suggested_tags=classification_result.suggested_tags,
                metadata=classification_result.metadata,
                source=classification_result.source,
            ),
            tags_created=tags_created,
            tags_added=tags_added,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"分類檔案失敗 (ID: {file_id}): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分類檔案失敗: {str(e)}",
        )


@router.get(
    "/{file_id}/classification",
    response_model=Optional[schemas.ClassificationResult],
    summary="查詢檔案的分類結果",
    description="""
    查詢檔案的分類結果（從註解中讀取最新的分類信息）。

    如果檔案尚未分類，返回 null。
    """,
)
def get_file_classification(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_optional),
):
    """查詢檔案的分類結果"""
    # 查詢檔案
    db_file = db.query(models.File).filter(models.File.id == file_id).first()
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"檔案不存在: {file_id}"
        )

    # 查詢最新的分類註解
    classification_annotation = (
        db.query(models.Annotation)
        .filter(
            models.Annotation.file_id == file_id, models.Annotation.source == "auto"
        )
        .order_by(models.Annotation.created_at.desc())
        .first()
    )

    if not classification_annotation:
        return None

    # 提取分類信息
    classification_data = classification_annotation.data.get("classification", {})

    return schemas.ClassificationResult(
        file_type=classification_data.get("file_type", "Unknown"),
        confidence=classification_data.get("confidence", 0.0),
        suggested_tags=classification_data.get("suggested_tags", []),
        metadata=classification_data.get("metadata", {}),
        source="auto",
    )


@router.get(
    "/classifications/stats",
    response_model=schemas.ClassificationStatsResponse,
    summary="查詢分類統計",
    description="""
    查詢所有已分類檔案的統計信息。

    包括：
    - 總檔案數
    - 各類型分佈
    - 平均置信度
    - 未分類檔案數量
    """,
)
def get_classification_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_optional),
):
    """查詢分類統計"""
    # 查詢所有分類註解
    classification_annotations = (
        db.query(models.Annotation).filter(models.Annotation.source == "auto").all()
    )

    if not classification_annotations:
        return schemas.ClassificationStatsResponse(
            total=0, by_type={}, avg_confidence=0.0, unknown_count=0, unknown_rate=0.0
        )

    # 統計
    type_counts: Dict[str, int] = {}
    total_confidence = 0.0
    unknown_count = 0

    # 使用字典去重（每個檔案只統計最新的分類）
    file_classifications: Dict[int, Dict[str, Any]] = {}

    for annotation in classification_annotations:
        file_id = annotation.file_id
        classification_data = annotation.data.get("classification", {})

        # 只保留最新的分類（按 annotation.id 判斷）
        if file_id not in file_classifications or annotation.id > file_classifications[
            file_id
        ].get("annotation_id", 0):
            file_classifications[file_id] = {
                "annotation_id": annotation.id,
                "file_type": classification_data.get("file_type", "Unknown"),
                "confidence": classification_data.get("confidence", 0.0),
            }

    # 統計去重後的數據
    for file_id, data in file_classifications.items():
        file_type = data["file_type"]
        confidence = data["confidence"]

        type_counts[file_type] = type_counts.get(file_type, 0) + 1
        total_confidence += confidence

        if file_type == "Unknown":
            unknown_count += 1

    total = len(file_classifications)

    return schemas.ClassificationStatsResponse(
        total=total,
        by_type=type_counts,
        avg_confidence=total_confidence / total if total > 0 else 0.0,
        unknown_count=unknown_count,
        unknown_rate=unknown_count / total if total > 0 else 0.0,
    )


@router.get(
    "/supported-types",
    response_model=Dict[str, List[str]],
    summary="查詢支援的檔案類型",
    description="返回系統支援的所有檔案類型及對應的擴展名",
)
def get_supported_file_types():
    """查詢支援的檔案類型"""
    return classification_service.get_supported_types()
