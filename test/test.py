#!/usr/bin/env python
# coding=utf-8
"""
Test Preprocessor
"""
# pylint: disable=line-too-long

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# pylint: disable=wrong-import-position
from zipfile import ZipFile  # noqa: E402
import requests  # noqa: E402
from radye.preprocessor import Preprocessor  # noqa: E402
from radye.utilities import ensure_exists, RYE_DATA, RYE_OUT  # noqa: E402
# pylint: enable=wrong-import-position


# for this test we use the data provided by the bratstoolkit
URL = "https://neuronflow.github.io/BraTS-Preprocessor/downloads/example_data.zip"  # noqa: E501

STUDY = "exam_import"
SUBJECT = "OtherEXampleFromTCIA"
T1W_NAME = "T1_AX_OtherEXampleTCIA_TCGA-FG-6692_Si_TCGA-FG-6692_T1_AX_SE_10_se2d1_t1.nii.gz"  # noqa: E501
T1C_NAME = "MRHR_T1_AX_POST_GAD_OtherEXampleTCIA_TCGA-FG-6692_Si_TCGA-FG-6692_MRHR_T1_AX_POST_GAD_SE_13_se2d1r_t1c.nii.gz"  # noqa: E501
T2W_NAME = "MRHR_T2_AX_OtherEXampleTCIA_TCGA-FG-6692_Si_TCGA-FG-6692_MRHR_T2_AX_SE_2_tse2d1_11_t2.nii.gz"  # noqa: E501
FLAIR_NAME = "MRHR_FLAIR_AX_OtherEXampleTCIA_TCGA-FG-6692_Si_TCGA-FG-6692_MRHR_FLAIR_AX_SE_IR_5_tir2d1_21_fla.nii.gz"  # noqa: E501

data_dir = ensure_exists(RYE_DATA)
local_path = data_dir / "example_data.zip"

ZIP_PATHS = {
    "T1w": f"{STUDY}/{SUBJECT}/{T1W_NAME}",
    "T1c": f"{STUDY}/{SUBJECT}/{T1C_NAME}",
    "T2w": f"{STUDY}/{SUBJECT}/{T2W_NAME}",
    "FLAIR": f"{STUDY}/{SUBJECT}/{FLAIR_NAME}",
}

OUTPUT_PATHS = {
    "T1w": data_dir / "example_T1w.nii.gz",
    "T1c": data_dir / "example_T1c.nii.gz",
    "T2w": data_dir / "example_T2w.nii.gz",
    "FLAIR": data_dir / "example_FLAIR.nii.gz",
}

download = all(path.is_file() for _, path in OUTPUT_PATHS.items())

# Download the file contents in binary format
if download:
    request = requests.get(URL)

    with local_path.open("wb") as fid:
        fid.write(request.content)

    # extracting 4 modalities from patient 'OtherEXampleFromTCIA'
    with ZipFile(local_path, "r") as zid:
        for mod, path in ZIP_PATHS.items():
            with OUTPUT_PATHS[mod].open("wb") as fid:
                fid.write(zid.read(path))
    print("Images have been downloaded and extracted properly.")
else:
    print("Images already downloaded.")

# Preprocessed data
pproc = Preprocessor(
    OUTPUT_PATHS,
    output_folder=RYE_OUT,
    reference="T1w",
    to_mni=True,
    crop=True,
)

pproc.run()
