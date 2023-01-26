mkdir -p output
mkdir -p input
docker run \
	--rm \
	-v ${PWD}:/workspace \
	-v ${PWD}/output:/output \
    -v ${PWD}/input:/input \
	radvisionen/ros-galactic-mcap-fuser
