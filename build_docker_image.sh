echo "Building docker image for desktop"
docker build \
  -t radvisionen/ros-galactic-mcap-fuser:latest \
  -f Dockerfile.galactic.desktop \
  .
