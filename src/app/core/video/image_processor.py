import cv2

from .output_strategy import build_image_write_params
from ..exceptions import FileReadError, FileSaveError, FrameProcessingError, ModelLoadError


def process_image(processor) -> None:
    """
    处理单张图片。
    """
    try:
        processor.status.emit("🖼️ 读取图片文件...")
        image = cv2.imread(processor.input_path)

        if image is None:
            raise FileReadError("无法读取图片文件", details=f"文件路径: {processor.input_path}")

        processor.logger.info(f"Image loaded: {image.shape}")
        processor.progress.emit(20)

        processing_params = {
            "auto_detect": processor.ai_params.get("auto_detect", True),
            "detection_sensitivity": processor.ai_params.get("detection_sensitivity", 0.5),
            "user_mask": processor.ai_params.get("user_mask", None),
        }

        processor.status.emit("🔍 检测水印区域...")
        processor.progress.emit(40)

        if processor.ai_handler is None:
            raise ModelLoadError("AI handler not initialized")

        processed_image, processing_info = processor.ai_handler.process_frame(
            image, processing_params
        )

        # 记录最后一次处理信息，便于批处理清单导出追溯
        processor.last_processing_info = processing_info
        if (
            isinstance(processing_info, dict)
            and "error" not in processing_info
            and int(processing_info.get("watermark_areas_found", 0) or 0) > 0
        ):
            processor.last_effective_processing_info = processing_info

        if "error" in processing_info:
            raise FrameProcessingError("帧处理失败", details=processing_info["error"])

        processor.progress.emit(80)
        processor.status.emit("🎨 修复水印区域...")

        areas_found = processing_info.get("watermark_areas_found", 0)
        processing_time = processing_info.get("processing_time", 0)
        method = processing_info.get("inpainting_method", "none")

        processor.last_processing_summary = {
            "media_type": "image",
            "watermark_areas_found": int(areas_found or 0),
            "processing_time_s": float(processing_time or 0),
            "inpainting_method": method,
        }

        processor.logger.info(
            f"Processing completed: {areas_found} watermark areas found, "
            f"method: {method}, time: {processing_time:.2f}s"
        )

        processor.status.emit("💾 保存处理后的图片...")

        write_params = build_image_write_params(
            processor.output_path,
            processor.ai_params,
            cv2_module=cv2,
        )
        save_success = (
            cv2.imwrite(processor.output_path, processed_image, write_params)
            if write_params
            else cv2.imwrite(processor.output_path, processed_image)
        )
        if not save_success:
            raise FileSaveError("保存图片失败", details=f"输出路径: {processor.output_path}")

        processor.progress.emit(100)
        processor.preview_update.emit(processed_image)
        processor.status.emit(f"✅ 处理完成! 发现 {areas_found} 个水印区域")
        processor.finished.emit(processor.output_path)

    except Exception as e:  # noqa: BLE001
        processor.logger.error(f"Image processing error: {e}")
        processor.error.emit(f"图片处理失败: {str(e)}")
