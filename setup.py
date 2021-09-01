from setuptools import setup, find_packages

setup(
    name='hius',
    version='0.1.1',
    description='Minimalistic ASGI web framework',
    long_description=open('README.md', 'r').read(),
    long_description_content_type='text/markdown',
    author='Nikita Ryabinin',
    author_email='ryabinin.ne@gmail.com',
    license='MIT',
    license_file='LICENSE',
    url='https://github.com/WoolenSweater/hius',
    packages=find_packages(exclude=['tests*']),
    install_requires=['starlette', 'pydantic'],
    extras_require={
        'uvicorn': ['uvicorn']
    },
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        "Topic :: Internet",
        'Topic :: Internet :: WWW/HTTP',
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9'
    ]
)
