echo "Building docker image for desktop"
sudo docker build \
  -t radvisionen/ros-galactic-mcap-fuser:latest \
  -f Dockerfile.galactic.desktop \
  .