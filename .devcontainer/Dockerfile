FROM python:3.12

####### PREPARE CUDA UBUNTU REPOSITORY #######
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
RUN dpkg -i cuda-keyring_1.1-1_all.deb
####### PREPARE CUDA UBUNTU REPOSITORY #######


####### DOWNLOAD ALL UBUNTU PACKAGES NEEDED FOR OPENCV #######
RUN apt-get update 
RUN apt-get upgrade -y

RUN DEBIAN_FRONTEND=noninteractive \
	apt-get install -y --no-install-recommends \
  tzdata \
  libgtk2.0-dev \
  pkg-config \
	libgstreamer1.0-0 \
	gstreamer1.0-plugins-base \
	gstreamer1.0-plugins-good \
	gstreamer1.0-plugins-bad \
	gstreamer1.0-plugins-ugly \
	gstreamer1.0-libav \
	gstreamer1.0-tools \
	gstreamer1.0-rtsp \
	libgstreamer1.0-dev \
	libgstreamer-plugins-base1.0-dev \
	git \
	# python3-pip \
	python3-venv \
	gcc \
	python3-dev \
	libxml2-dev \
	libxslt-dev \
	build-essential \
	libssl-dev \
	cmake \
	cuda-toolkit
####### DOWNLOAD ALL UBUNTU PACKAGES NEEDED FOR OPENCV #######


####### COMPILE OPENCV W/ CUDA & GSTREAMER SUPPORT #######
# Doesn't compile with HVENC support
WORKDIR /opencv-install
COPY detector-worker/requirements-with-opencv.txt /opencv-install/requirements-with-opencv.txt

# CREATE VENV
RUN python3 -m venv /opt/venv
ENV PATH /opt/venv/bin:$PATH

# INSTALL PYTHON PACKAGES THAT CONTAIN OPENCV AS A DEPENDENCY (AND REMOVE OPENCV)
RUN pip3 install numpy future lxml pymavlink setuptools
RUN pip3 install -r requirements-with-opencv.txt
RUN pip3 uninstall -y opencv-python

# BUILD OPENCV
RUN git clone https://github.com/opencv/opencv_contrib.git
RUN git clone https://github.com/opencv/opencv.git
RUN \
	cd opencv && \
	git submodule update --recursive --init && \
	mkdir build && \
	cd build && \
	cmake \
	-D CMAKE_BUILD_TYPE=RELEASE \
	-D PYTHON_EXECUTABLE=$(which python3) \
	-D BUILD_opencv_python2=OFF \
	-D CMAKE_INSTALL_PREFIX=$(python3 -c "import sys; print(sys.prefix)") \
	-D PYTHON3_EXECUTABLE=$(which python3) \
	-D PYTHON3_INCLUDE_DIR=$(python3 -c "from distutils.sysconfig import get_python_inc; print(get_python_inc())") \
	-D PYTHON3_PACKAGES_PATH=$(python3 -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())") \
	-D OPENCV_EXTRA_MODULES_PATH=/opencv-install/opencv_contrib/modules/ \
	-D WITH_GSTREAMER=ON \
	-D WITH_CUDA=ON \
	-D WITH_CUDNN=ON \
	-D CUDA_ARCH_BIN=8.6 .. && \
	make -j$(nproc) && \
	make install && \
	ldconfig
####### COMPILE OPENCV W/ CUDA & GSTREAMER SUPPORT #######

####### CLEAN UP COMPILATION #######
RUN rm -rf /opencv-install
RUN apt-get -qq autoremove
RUN apt-get -qq clean
####### CLEAN UP COMPILATION #######


####### INSTALL NEOVIM #######
WORKDIR /neovim-install
ENV PATH "$PATH:/opt/nvim-linux64/bin"
RUN curl -LO https://github.com/neovim/neovim/releases/latest/download/nvim-linux64.tar.gz
RUN rm -rf /opt/nvim
RUN tar -C /opt -xzf nvim-linux64.tar.gz
RUN git clone https://github.com/NvChad/starter ~/.config/nvim

RUN apt install npm -y
RUN npm install -g pyright
####### INSTALL NEOVIM #######


####### BASE ########
WORKDIR /app
COPY detector-worker/requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt --prefer-binary

WORKDIR /workspaces
