# Fuse Downloaded Combo Bags into one Rosbag

`DLR Holoscene` and `DLR SDP` platforms record sensor data into a ZIP file.
Use this repository to convert it into a single rosbag for further analysis and visualization.

Tested on Ubuntu 20.04 and macOS Monterey (note: slow performance on M1 due to architecture mismatch)

## Quickstart

1. Clone this repository:

```
git clone https://github.com/borealbikes-dev/combo-rosbag-fuser.git
```

2. Install [Docker](https://docs.docker.com/engine/install/) for your system. Once installed, confirm installation by:

```
docker -v
```

On a Mac, you may need to run the Docker application (so that it shows up on the top bar) as well.

In case `docker` requires you to run it with `sudo`, run the below scripts with `sudo` as well.

3. Run the main script to download the latest docker image and to create the `input` and `output` directories.

```
./run_fuser.sh
```

4. Move/copy the ZIP file obtained from the Boreal Web Interface into the `input` directory.

5. Then run the script again:

```
./run_fuser.sh
```

6. See `output` directory for a new `.mcap` rosbag.

7. Use [Foxglove](https://foxglove.dev/) to view its contents.

## Anatomy of combo_bag

An unzipped combo_bag looks something like this:
```
combo_bag_2023-01-25_17-03-15/  # date format: YYYY-MM-DD_HH-MM-SS
├── camera
│   └── usb2 # a directory for each camera source
│       ├── usb-1674662595562-ms-000-minutes.mp4  # filename contains start of video for this camera in milliseconds (since linux epoch)
│       └── usb-1674662595562-ms-001-minutes.mp4  # files are split by 1 minute when recording 
└── rosbag
    ├── metadata.yaml
    ├── rosbag_0.mcap # rosbag for first minute
    └── rosbag_1.mcap # rosbag for second minute 
```
