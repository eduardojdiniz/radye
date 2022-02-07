# radye

This repository provides a simple pipeline to co-register different imaging modalities and skull strip them.

This package uses HD-BET (https://github.com/MIC-DKFZ/HD-BET) and ANTsPy (https://github.com/ANTsX/ANTsPy).

## To install the package:
```
pip install  git+https://github.com/eduardojdiniz/radye#egg=radye
```

## Example case 1:
Let's assume we have access to 4 imaging modalities (e.g. T1w, T1c, T2w, FLAIR) and we want to:
- co-register the scans using T1w as reference
- in the MNI space (1x1x1 mm)
- skull strip the scans using T1w as reference
- crop the skull-stripped scans to remove the zero padding

```python
import radye as rye
paths = {
    'T1w':'./data/example_T1w.nii.gz',
    'T1c':'./data/example_T1c.nii.gz',
    'T2w':'./data/example_T2w.nii.gz',
    'FLAIR':'./data/example_FLAIR.nii.gz',
}

ppr = rye.Preprocessor(
    paths,
    output_folder = './output',
    label_path=None,
    prefix='example_',
    reference='T1w',
    do_skull_stripping=True,
    do_coregistration=True,
    to_mni=True,
    crop=True)
)

ppr.run()
```
The output folder will contain three folders nammed `coregistration`, `skullstripping` and `cropping` containing respectively the co-registered modalities, the skull-stripped and co-registered imaging modalities and the cropped versions of these latter skull-stripped scans. (example output `'./output/cropping/example_T1w.nii.gz'`)

## Example case 2:
Let's assume we have access to 4 **co-registered** imaging modalities (e.g. T1w, T1c, T2w, FLAIR) and we want to:
- co-registered them in the MNI space (1x1x1 mm) using T1w as reference
- skull strip the scans using T1w as reference
- crop the skull-stripped scans to remove the zero padding

```python
import radye as rye
paths = {
    'T1w':'./data/example_T1w.nii.gz',
    'T1c':'./data/example_T1c.nii.gz',
    'T2w':'./data/example_T2w.nii.gz',
    'FLAIR':'./data/example_FLAIR.nii.gz',
}

ppr = rye.Preprocessor(
    paths,
    output_folder = './output',
    label_path=None,
    prefix='example_',
    reference='T1w',
    do_skull_stripping=True,
    do_coregistration=False,
    to_mni=True,
    crop=True)
)

ppr.run()
```
The output folder will contain three folders nammed `coregistration`, `skullstripping` and `cropping` containing respectively the co-registered modalities in the MNI space, the skull-stripped and co-registered imaging modalities and the cropped versions of these latter skull-stripped scans. (example output `'./output/cropping/example_T1w.nii.gz'`)


## Example case 3:
Let's assume we have access to 4 imaging modalities (e.g. T1w, T1c, T2w, FLAIR) one segmentation drawn on the T1c scan. We want to:
- co-register the scans using T1c as reference
- in the MNI space (1x1x1 mm), including the labelmap
- skull strip the scans using T1c as reference
- crop the skull-stripped scans to remove the zero padding and apply the same cropping to the registered labelmap

**Note that the reference scan must be the scan employed for the segmentation, here the T1c scan.**
```python
import radye as rye
paths = {
    'T1w':'./data/example_T1w.nii.gz',
    'T1c':'./data/example_T1c.nii.gz',
    'T2w':'./data/example_T2w.nii.gz',
    'FLAIR':'./data/example_FLAIR.nii.gz',
}

ppr = rye.Preprocessor(
    paths,
    output_folder = './output',
    label_path='./data/example_Label.nii.gz',
    prefix='example_',
    reference='T1c',
    do_skull_stripping=True,
    do_coregistration=True,
    to_mni=True,
    crop=True)
)

ppr.run()
```
The output folder will contain three folders nammed `coregistration`, `skullstripping` and `cropping` containing respectively the co-registered modalities and labelmap, the skull-stripped and co-registered imaging modalities and labelmap and the cropped versions of these latter skull-stripped scans. (example output `'./output/cropping/example_T1w.nii.gz'`)
