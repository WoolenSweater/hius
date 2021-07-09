from setuptools import setup, find_packages

setup(
    name='hius',
    version='0.1.0',
    description='Lightweight ASGI web framework',
    long_description=open('README.md', 'r').read(),
    long_description_content_type='text/markdown',
    author='Nikita Ryabinin',
    author_email='ryabinin.ne@gmail.com',
    license='MIT',
    license_file='LICENSE',
    url='https://github.com/WoolenSweater/huis',
    packages=find_packages(exclude=['tests*']),
    install_requires=['starlette', 'pydantic'],
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 3 - Alpha',
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
