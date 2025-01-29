"""
Modified from SRXToolsExportTiff

"""


import os
from SRXTools import initExperimentDir, readImageStackAsUint16, readImageStackAsUint16_edit, writeImageStackAsTiff


def get_files(file_path: str = None) -> list:
    """
    Scan the directory for the files
    """
    return [f.path for f in os.scandir(file_path) if f.is_dir()]


class PARS:
    data_folder = 'I:\Data base\\Nanotube\PGP1F'
    input_dir = os.path.join(data_folder, 'raw_data')
    out_path = os.path.join(data_folder, 'raw_data_tiff')
    rounds = 5
    probes = channels = 5


def main():
    print("Converting the raw data to .tiff data format")
    if not os.path.exists(PARS.out_path):
        os.makedirs(PARS.out_path)
    probe = PARS.channels

    raw_data_dirs = sorted(get_files(PARS.input_dir))

    for nc in range(len(raw_data_dirs)):
        bn1 = os.path.splitext(os.path.basename(raw_data_dirs[nc]))[0]
        locs_path = sorted(get_files(raw_data_dirs[nc]))
        print(nc, locs_path)
        n_loc = len(locs_path)
        for nl in range(n_loc):
            exp_dir = locs_path[nl]
            print(f'processing dir {nc}, location {nl}')
            success = initExperimentDir(exp_dir)
            if not success:
                print("Failed to initialize SRXTools!")
                exit(1)

            img_stack = readImageStackAsUint16_edit(exp_dir, probe)
            print(nl, img_stack.dtype, img_stack.shape)

            for j in range(probe):
                fn_p2 = os.path.splitext(os.path.basename(exp_dir))[0]
                out_fn = os.path.join(PARS.out_path, bn1 + fn_p2 + f'_p{j+1}' + '.tiff')
                img_tmp = img_stack[j, :, :, :]
                writeImageStackAsTiff(img_tmp, out_fn)

            del (img_stack)
            del (img_tmp)


if __name__ == '__main__':
    main()





