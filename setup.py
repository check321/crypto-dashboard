from setuptools import setup, find_packages

setup(
    name="my_fastapi_project",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
        "pydantic-settings",
        # 其他依赖...
    ],
) 