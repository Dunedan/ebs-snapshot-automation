from setuptools import setup

setup(name='ebs-snapshot-automation',
    version='0.1',
    description='A small script meant to be run as a cronjob to regularly snapshot EBS volumes attached to EC2 instances and handle rolling backups for these snapshots.',
    url='http://github.com/smaato/ebs-snapshot-automation',
    author='Daniel Roschka',
    author_email='daniel@smaato.com',
    license='MIT',
    scripts=['ebs_snapshot_automation.py'],
    zip_safe=False,
    install_requires=['boto3'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ],
)
