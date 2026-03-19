#!/usr/bin/env python3
"""
Test video preview functionality
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")
pytest.importorskip("PyQt6")


def test_extract_video_first_frame():
    """Test extracting first frame from video"""
    print("=" * 60)
    print("Test 1: Extract first frame from video")
    print("=" * 60)

    # Create test video
    test_video_path = "test_output/test_video.mp4"
    os.makedirs("test_output", exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(test_video_path, fourcc, 30.0, (640, 480))

    for i in range(30):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :, 0] = i * 8
        frame[:, :, 1] = 128
        frame[:, :, 2] = 255 - i * 8
        out.write(frame)

    out.release()
    print(f"[OK] Test video created: {test_video_path}")

    # Extract first frame
    cap = cv2.VideoCapture(test_video_path)
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            print(f"[OK] First frame extracted: shape={frame_rgb.shape}, dtype={frame_rgb.dtype}")
            assert frame_rgb.shape == (480, 640, 3)
            assert frame_rgb.dtype == np.uint8
            print("[PASS] First frame extraction test")
        else:
            print("[FAIL] Failed to read first frame")
            return False
    else:
        print("[FAIL] Failed to open video")
        return False

    os.remove(test_video_path)
    print()
    return True


def test_numpy_to_qimage():
    """Test numpy array to QImage conversion"""
    print("=" * 60)
    print("Test 2: numpy array to QImage")
    print("=" * 60)

    from PyQt6.QtGui import QImage, QPixmap

    test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    h, w, c = test_image.shape
    bytes_per_line = 3 * w
    q_image = QImage(test_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

    if not q_image.isNull():
        print(f"[OK] QImage created: size={q_image.size().width()}x{q_image.size().height()}")

        pixmap = QPixmap.fromImage(q_image)
        if not pixmap.isNull():
            print(f"[OK] QPixmap created: size={pixmap.size().width()}x{pixmap.size().height()}")
            print("[PASS] numpy to QImage/QPixmap test")
            print()
            return True
        else:
            print("[FAIL] QPixmap creation failed")
            return False
    else:
        print("[FAIL] QImage creation failed")
        return False


def test_video_metadata():
    """Test video metadata reading"""
    print("=" * 60)
    print("Test 3: Video metadata reading")
    print("=" * 60)

    test_video_path = "test_output/test_video_meta.mp4"
    os.makedirs("test_output", exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(test_video_path, fourcc, 25.0, (1920, 1080))

    for i in range(50):
        frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        out.write(frame)

    out.release()

    cap = cv2.VideoCapture(test_video_path)

    if cap.isOpened():
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        print(f"[OK] Resolution: {width}x{height}")
        print(f"[OK] FPS: {fps:.2f}")
        print(f"[OK] Frame count: {frame_count}")
        print(f"[OK] Duration: {duration:.2f} seconds")

        assert width == 1920
        assert height == 1080
        assert fps == 25.0
        assert frame_count == 50

        print("[PASS] Video metadata reading test")
        print()

        os.remove(test_video_path)
        return True
    else:
        print("[FAIL] Failed to open video")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Video Preview Functionality Test Suite")
    print("=" * 60 + "\n")

    results = []
    results.append(("First frame extraction", test_extract_video_first_frame()))
    results.append(("numpy to QImage", test_numpy_to_qimage()))
    results.append(("Video metadata reading", test_video_metadata()))

    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {name}")

    print()
    print(f"Total: {passed}/{total} passed")

    if passed == total:
        print("\nAll tests passed! Video preview functionality works correctly.")
        sys.exit(0)
    else:
        print(f"\n{total - passed} test(s) failed.")
        sys.exit(1)
