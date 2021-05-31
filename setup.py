from setuptools import setup, find_packages

setup(
    name='liteapi',
    version='0.0.3',
    packages=find_packages(),
    description='Lightweight ASGI web framework',
    long_description=open('README.md', 'r').read(),
    long_description_content_type='text/markdown',
    author='Nikita Ryabinin',
    author_email='ryabinin.ne@gmail.com',
    license='MIT',
    license_file='LICENSE',
    install_requires=['starlette'],
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Web Environment',
        'Topic :: Internet :: WWW/HTTP',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9'
    ]
)
