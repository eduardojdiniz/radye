#!/usr/bin/env python
# coding=utf-8
"""
Test Preprocessor
"""
# pylint: disable=line-too-long

import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

# pylint: disable=wrong-import-position
from radye.preprocessor import Preprocessor  # noqa: E402
from radye.utilities import download_test_data, RYE_OUT  # noqa: E402
# pylint: enable=wrong-import-position

# Download test data
output_paths = download_test_data()

# Preprocessed data
pproc = Preprocessor(
    output_paths,
    output_folder=RYE_OUT,
    reference="T1w",
    to_mni=True,
    crop=True,
)

pproc.run()
