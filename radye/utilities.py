#!/usr/bin/env python
# coding=utf-8
"""
Utilities
"""
# pylint: disable=line-too-long

from pathlib import Path
from typing import Union, List, Dict
from zipfile import ZipFile  # noqa: E402
import requests  # noqa: E402
import ants  # type: ignore
import torchio as tio  # type: ignore
import nibabel as nib  # type: ignore
import SimpleITK as sitk  # type: ignore
import numpy as np
import radye as rye

__all__ = [
    "PathType",
    "crop_scans",
    "get_mni",
    "RYE_ROOT",
    "RYE_SRC",
    "RYE_OUT",
    "RYE_DATA",
    "RYE_CONF",
    "download_test_data",
]

PathType = Union[str, Path]

module_path = Path(rye.__file__)
RYE_SRC = module_path.parents[0].absolute()
RYE_ROOT = module_path.parents[1].absolute()
RYE_OUT = RYE_ROOT / "output"
RYE_DATA = RYE_ROOT / "data"
RYE_CONF = RYE_ROOT / "conf"


def find_zeros(img_array):
    if len(img_array.shape) == 4:
        img_array = np.amax(img_array, axis=3)
    assert len(img_array.shape) == 3
    x_dim, y_dim, z_dim = tuple(img_array.shape)
    x_zeros, y_zeros, z_zeros = np.where(img_array == 0.0)
    # x-plans that are not uniformly equal to zeros

    try:
        (x_to_keep, ) = np.where(np.bincount(x_zeros) < y_dim * z_dim)
        x_min = min(x_to_keep)
        x_max = max(x_to_keep) + 1
    except Exception:
        x_min = 0
        x_max = x_dim
    try:
        (y_to_keep, ) = np.where(np.bincount(y_zeros) < x_dim * z_dim)
        y_min = min(y_to_keep)
        y_max = max(y_to_keep) + 1
    except Exception:
        y_min = 0
        y_max = y_dim
    try:
        (z_to_keep, ) = np.where(np.bincount(z_zeros) < x_dim * y_dim)
        z_min = min(z_to_keep)
        z_max = max(z_to_keep) + 1
    except:
        z_min = 0
        z_max = z_dim
    return x_min, x_max, y_min, y_max, z_min, z_max


def crop_scans(reference: str, inputs: List[Path], outputs: List[Path]):
    img_crop = nib.load(reference)
    img_crop_data = img_crop.get_fdata()
    x_min, x_max, y_min, y_max, z_min, z_max = find_zeros(img_crop_data)

    x_max = img_crop_data.shape[0] - x_max
    y_max = img_crop_data.shape[1] - y_max
    z_max = img_crop_data.shape[2] - z_max
    bounds_parameters = [x_min, x_max, y_min, y_max, z_min, z_max]
    low = bounds_parameters[::2]
    high = bounds_parameters[1::2]
    low = [int(k) for k in low]
    high = [int(k) for k in high]

    for input_path, output_path in zip(inputs, outputs):
        image = sitk.ReadImage(str(input_path))
        image = sitk.Crop(image, low, high)
        sitk.WriteImage(image, str(output_path))


def ensure_exists(path: PathType) -> Path:
    """
    Enforce the directory existence.
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_mni(skull_stripped: bool = True) -> ants.ANTsImage:
    """
    Get MNI template.

    Parameters
    ----------
    skull_stripped : bool, optional
        If ``True``, return the skull-stripped template. Default = ``True``.

    Returns
    -------
    _ : ants.Image
        Return the MNI template wrapped in an ants.Image.
    Default = ``skull-stripped MNI ants.Image template.
    """
    path_mni = RYE_DATA / "mni.nii.gz"
    path_mni_brain = RYE_DATA / "mni_brain.nii.gz"
    if not path_mni.is_file() or not path_mni_brain.is_file():
        print("MNI template not found. Using the ICBM2009C Template")
        icbm2009c = tio.datasets.ICBM2009CNonlinearSymmetric()
        path_mni = icbm2009c["t1"].path
        path_mni_brain = icbm2009c["brain"].path
    if skull_stripped:
        return ants.image_read(str(path_mni_brain))
    return ants.image_read(str(path_mni))


def download_test_data() -> Dict[str, Path]:
    """Download data provided by the bratstoolkit"""

    url = "https://neuronflow.github.io/BraTS-Preprocessor/downloads/example_data.zip"  # noqa: E501
    study = "exam_import"
    subject = "OtherEXampleFromTCIA"
    t1w_name = "T1_AX_OtherEXampleTCIA_TCGA-FG-6692_Si_TCGA-FG-6692_T1_AX_SE_10_se2d1_t1.nii.gz"  # noqa: E501
    t1c_name = "MRHR_T1_AX_POST_GAD_OtherEXampleTCIA_TCGA-FG-6692_Si_TCGA-FG-6692_MRHR_T1_AX_POST_GAD_SE_13_se2d1r_t1c.nii.gz"  # noqa: E501
    t2w_name = "MRHR_T2_AX_OtherEXampleTCIA_TCGA-FG-6692_Si_TCGA-FG-6692_MRHR_T2_AX_SE_2_tse2d1_11_t2.nii.gz"  # noqa: E501
    flair_name = "MRHR_FLAIR_AX_OtherEXampleTCIA_TCGA-FG-6692_Si_TCGA-FG-6692_MRHR_FLAIR_AX_SE_IR_5_tir2d1_21_fla.nii.gz"  # noqa: E501

    data_dir = ensure_exists(RYE_DATA)
    local_path = data_dir / "example_data.zip"

    zip_paths = {
        "T1w": f"{study}/{subject}/{t1w_name}",
        "T1c": f"{study}/{subject}/{t1c_name}",
        "T2w": f"{study}/{subject}/{t2w_name}",
        "FLAIR": f"{study}/{subject}/{flair_name}",
    }

    output_paths = {
        "T1w": data_dir / "example_T1w.nii.gz",
        "T1c": data_dir / "example_T1c.nii.gz",
        "T2w": data_dir / "example_T2w.nii.gz",
        "FLAIR": data_dir / "example_FLAIR.nii.gz",
    }

    is_downloaded = all(path.is_file() for _, path in output_paths.items())

    # Download the file contents in binary format
    if not is_downloaded:
        request = requests.get(url)

        with local_path.open("wb") as fid:
            fid.write(request.content)

        # extracting 4 modalities from patient 'OtherEXampleFromTCIA'
        with ZipFile(local_path, "r") as zid:
            for mod, path in zip_paths.items():
                with output_paths[mod].open("wb") as fid:
                    fid.write(zid.read(path))

        # remove .zip file
        local_path.unlink()
        print("Images have been downloaded and extracted properly.")
    else:
        print("Images already downloaded.")

    return output_paths
