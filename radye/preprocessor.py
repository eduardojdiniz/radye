#!/usr/bin/env python
# coding=utf-8
"""
Preprocessor
"""

from typing import Dict
from pathlib import Path
import ants  # type: ignore
from HD_BET.run import run_hd_bet  # type: ignore
import nibabel as nib  # type: ignore
import SimpleITK as sitk  # type: ignore
import torch

from .utilities import PathType, crop_scans, get_mni, RYE_OUT, ensure_exists


class Preprocessor:
    """
    Base class for data processors.

    To create a subclass, you need to implement the following functions:

    A BaseDataModule needs to implement 6 key methods:
    <__init__>:
        (Optionally) Initialize the class, first call super.__init__().
    <prepare_data>:
        Things to do on 1 GPU/TPU not on every GPU/TPU in distributed mode.
    <setup>:
        Things to do on every accelerator in distributed mode.
    <train_dataloader>:
        The training dataloader.
    <val_dataloader>:
        The validation dataloader(s).
    <test_dataloader>:
        The test dataloader(s).
    <predict_dataloader>:
        The prediction dataloader(s).
    <teardown>:
        Things to do on every accelerator in distributed mode when finished.

    Typical Workflow
    ----------------
    proc = Preprocessor()
    proc.prepare_data() # download
    proc.setup(stage) # process and split
    proc.teardown(stage) # clean-up

    Parameters
    ----------
    subject_dict : Dict[str, PathType]
        Dictionary with the image paths.
    output_folder : PathType
        Path to the output directory
    label_path : PathType, optional
        Path to the Label map. Default = ``None``.
    prefix : str, optional
        Optional prefix to be prepended to the output filenames.
        Default = ``None``.
    reference: str, optional
        Name of the modality be used as the reference. Default = ``None``.
    do_skull_stripping : bool, optional
        If ``True``, skull strip the images. Default = ``False``.
    do_coregistration : bool, optional
        If ``True``, co-register the images. Default = ``False``.
    to_mni : bool, optional
        If ``True``, register images to the MNI frame of reference.
        Default = ``True``.
    crop : bool, optional
        If ``True``, remove zero padding from the images. Default = ``False``.
    """

    def __init__(
        self,
        subject_dict: Dict[str, Path],
        output_folder: PathType = RYE_OUT,
        label_path: PathType = None,
        prefix: str = None,
        reference: str = None,
        do_skull_stripping: bool = False,
        do_coregistration: bool = False,
        to_mni: bool = False,
        crop: bool = False,
    ):

        self.subject_dict = subject_dict
        self.modalities = subject_dict.keys()
        self.output_folder = Path(output_folder)
        self.label_path = Path(label_path) if label_path else None
        self.prefix = prefix if prefix else ""
        self.do_skull_stripping = do_skull_stripping
        self.do_coregistration = do_coregistration
        self.to_mni = to_mni
        self.crop = crop

        if reference is None:
            self.reference = sorted(self.modalities)[0]
        else:
            assert (reference in subject_dict.keys(
            )), "Reference has to be one the imaging modality in subject_dict"
            self.reference = reference

        # Test files exist
        for mod in subject_dict.keys():
            assert subject_dict[mod].is_file(
            ), f"{subject_dict[mod]} doesn't exist"
        if self.label_path is not None:
            assert self.label_path.is_file(), "Label map doesn't exist"

        # Get mni if needed
        if self.to_mni:
            self.mni_img = get_mni(self.do_skull_stripping)

        # Create relevant folders if needed
        self.coregistration_folder = ensure_exists(self.output_folder /
                                                   "coregistration")
        if self.do_skull_stripping:
            self.skullstrip_folder = ensure_exists(self.output_folder /
                                                   "skullstripping")
        else:
            self.skullstrip_folder = self.coregistration_folder

        if crop:
            self.cropping_folder = ensure_exists(self.output_folder /
                                                 "cropping")

        self.device = 0 if torch.cuda.is_available() else "cpu"

    @staticmethod
    def _save_scan(img, name, save_folder: PathType):
        save_folder = ensure_exists(save_folder)
        output_filename = save_folder / f"{name}.nii.gz"
        ants.image_write(img, str(output_filename))

    @staticmethod
    def _apply_mask(input_path, output_path, reference, mask):
        input_img = sitk.ReadImage(str(input_path))
        ref_img = sitk.ReadImage(str(reference))
        output_img = sitk.Resample(
            input_img,
            ref_img,
            sitk.Transform(),
            sitk.sitkNearestNeighbor,
        )
        sitk.WriteImage(output_img, str(output_path))

        # Apply mask
        output_img = nib.load(str(output_path))
        output_affine = output_img.affine
        output_data = output_img.get_fdata()

        mask_data = nib.load(mask).get_fdata()

        output_data[mask_data == 0] = 0
        output_img = nib.Nifti1Image(output_data, output_affine)
        nib.save(output_img, str(output_path))

    def _run_coregistration(self):
        img_reference = ants.image_read(str(self.subject_dict[self.reference]))

        # Register the reference to MNI, if needed
        if self.to_mni:
            print("[INFO] Registering to MNI space using ANTsPy")
            print(f"{self.reference} is used as reference")
            reg = ants.registration(self.mni_img, img_reference, "Affine")
            img_reference = reg["warpedmovout"]
            self._save_scan(
                img_reference,
                f"{self.prefix}{self.reference}",
                self.coregistration_folder,
            )
            reg_tomni = reg["fwdtransforms"]
            if self.label_path is not None:
                img_label = ants.image_read(str(self.label_path))
                warped_label = ants.apply_transforms(
                    self.mni_img,
                    img_label,
                    reg_tomni,
                    interpolator="nearestNeighbor")
                self._save_scan(warped_label, f"{self.prefix}Label",
                                self.coregistration_folder)
        else:
            self._save_scan(
                img_reference,
                f"{self.prefix}{self.reference}",
                self.coregistration_folder,
            )
            if self.label_path is not None:
                img_label = ants.image_read(str(self.label_path))
                self._save_scan(img_label, f"{self.prefix}Label",
                                self.coregistration_folder)

        # Register the other scans, if needed
        modalities_toregister = list(self.modalities)
        modalities_toregister.remove(self.reference)
        for mod in modalities_toregister:
            if self.do_coregistration:
                # if the scans are already co-registered we reuse the ref to
                # MNI transformation
                if self.to_mni:
                    img_mod = ants.image_read(str(self.subject_dict[mod]))
                    warped_img = ants.apply_transforms(self.mni_img,
                                                       img_mod,
                                                       reg_tomni,
                                                       interpolator="linear")
                    self._save_scan(warped_img, f"{self.prefix}{mod}",
                                    self.coregistration_folder)
                    print(f"[INFO] Registration performed to MNI for {mod}")
                else:
                    img_mod = ants.image_read(str(self.subject_dict[mod]))
                    self._save_scan(img_mod, f"{self.prefix}{mod}",
                                    self.coregistration_folder)
                    print(f"No co-registration performed for {mod}")

            else:  # Scans are not co-registered
                img_mod = ants.image_read(str(self.subject_dict[mod]))
                reg = ants.registration(img_reference, img_mod, "Affine")
                self._save_scan(
                    reg["warpedmovout"],
                    f"{self.prefix}{mod}",
                    self.coregistration_folder,
                )
                print(
                    f"[INFO] Registration using ANTsPy for {mod} ",
                    f"with {self.reference} as reference",
                )

    def _run_skullstripping(self):
        print("[INFO] Performing Skull Stripping using HD-BET")
        pre = self.prefix
        ref = self.reference
        ref_co = self.coregistration_folder / f"{pre}{ref}.nii.gz"
        ref_sk = self.skullstrip_folder / f"{pre}{ref}.nii.gz"
        mask_sk = self.skullstrip_folder / f"{pre}{ref}_mask.nii.gz"
        run_hd_bet(str(ref_co), str(ref_sk), device=self.device)

        modalities_tosk = list(self.modalities)
        modalities_tosk.remove(self.reference)
        for mod in modalities_tosk:
            registered_mod = self.coregistration_folder / f"{pre}{mod}.nii.gz"
            skullstripped_mod = self.skullstrip_folder / f"{pre}{mod}.nii.gz"
            self._apply_mask(
                input_path=registered_mod,
                output_path=skullstripped_mod,
                reference=ref_sk,
                mask=mask_sk,
            )

        if self.label_path is not None:
            registered_lab = self.coregistration_folder / f"{pre}Label.nii.gz"
            skullstripped_lab = self.skullstrip_folder / f"{pre}Label.nii.gz"
            self._apply_mask(
                input_path=registered_lab,
                output_path=skullstripped_lab,
                reference=ref_sk,
                mask=mask_sk,
            )

    def _run_cropping(self):
        print("[INFO] Performing Cropping")
        pre = self.prefix
        ref = self.reference
        ref_sk = self.skullstrip_folder / f"{pre}{ref}.nii.gz"

        sk_images = [
            self.skullstrip_folder / f"{pre}{mod}.nii.gz"
            for mod in self.modalities
        ]
        cropped_images = [
            self.cropping_folder / f"{pre}{mod}.nii.gz"
            for mod in self.modalities
        ]

        if self.label_path is not None:
            sk_images.append(self.skullstrip_folder / f"{pre}Label.nii.gz")
            cropped_images.append(self.cropping_folder / f"{pre}Label.nii.gz")

        crop_scans(ref_sk, sk_images, cropped_images)

    def run(self):
        """Run the required preprocessing steps."""
        self._run_coregistration()
        if self.do_skull_stripping:
            self._run_skullstripping()
        if self.crop:
            self._run_cropping()
