# `SYS4INI.BIN` and `.AII` files

These files contain the metadata of the files is packed in the `.ALF` files.

- `SYS4INI.BIN` ususally from the original game. It usually contains metadata for the `DATA1.ALF`, `DATA2.ALF`, etc. files.
- `.AII` files will have accompany file with the same name with the `.ALF` extension. They are from append contents (`APPEND01`, `APPEND02`, etc).

# `.ALF` files

These files only contain the archive entries data back by back. It contains no file name, offset, size so that is why we need the `.AII` files or `SYS4INI.BIN` file to extract the contents.

# `.AGF` files

TODO

# Usage

- Generate metadata from from `SYS4INI.BIN` and `.AII` files by running [`process_metadata_file.py`](./process_metadata_file.py)

```
usage: process_metadata_file.py [-h] inpath [outdir]

Extract metadata from sys4ini.bin or *.aai files

positional arguments:
  inpath      input file or directory to search for sys4ini.bin or *.aai files
  outdir      output directory to save extracted metadata info

optional arguments:
  -h, --help  show this help message and exit
```

- The script would generate a pickle file `f'metadata-list-{time.time_ns()}.pickle'` in the output directory.
- The file would then serve as the input for other applications.

- [`unpack_all_images.py`](./unpack_all_images.py)

```
usage: unpack_all_images.py [-h] [--output-format {png,bmp,jpg}] [--force]
                            inpath outpath

Unpack all images from a pickle metadata file log.

positional arguments:
  inpath                path to the pickle log
  outpath               path to the output directory

optional arguments:
  -h, --help            show this help message and exit
  --output-format {png,bmp,jpg}
                        output format
  --force               overwrite existing files
```

Use the generated pickle file to extract the assets.
