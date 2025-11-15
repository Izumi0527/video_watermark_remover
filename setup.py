#!/usr/bin/env python3
"""
智能视频水印去除工具 - 安装配置文件
"""

import os

from setuptools import find_packages, setup


# 读取README文件
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return "智能视频水印去除工具 - AI驱动的水印检测和去除应用"


# 读取requirements文件
def read_requirements(filename):
    requirements = []
    req_path = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(req_path):
        with open(req_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 跳过注释和空行
                if line and not line.startswith("#") and not line.startswith("-r"):
                    # 处理内联注释
                    if "#" in line:
                        line = line.split("#")[0].strip()
                    if line:
                        requirements.append(line)
    return requirements


# 基础依赖
install_requires = read_requirements("requirements-minimal.txt")

# 可选依赖组
extras_require = {
    "full": read_requirements("requirements.txt"),
    "dev": read_requirements("requirements-dev.txt"),
    "minimal": install_requires,
}

setup(
    name="video-watermark-remover",
    version="0.3.0",
    author="Claude Code Assistant",
    author_email="noreply@anthropic.com",
    description="智能视频水印去除工具 - AI驱动的水印检测和去除应用",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/video-watermark-remover",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
        "Topic :: Multimedia :: Video :: Conversion",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Environment :: X11 Applications :: Qt",
    ],
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require=extras_require,
    entry_points={
        "console_scripts": [
            "video-watermark-remover=main:main",
            "vwr=main:main",
        ],
        "gui_scripts": [
            "video-watermark-remover-gui=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "app": [
            "*.py",
            "configs/*.ini",
            "assets/*",
        ],
    },
    keywords=[
        "watermark",
        "removal",
        "video",
        "image",
        "ai",
        "opencv",
        "computer-vision",
        "inpainting",
        "gui",
        "pyqt6",
        "batch-processing",
    ],
    project_urls={
        "Bug Reports": "https://github.com/yourusername/video-watermark-remover/issues",
        "Source": "https://github.com/yourusername/video-watermark-remover",
        "Documentation": "https://github.com/yourusername/video-watermark-remover/wiki",
    },
    zip_safe=False,  # PyQt6应用通常不适合zip安装
)
