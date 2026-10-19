#!/bin/sh
set -eu
if [ "$#" -ne 2 ]; then
    echo "Usage: sh Rebuild-Kernel.sh /absolute/linux-kernel-source /absolute/new-build-directory"
    exit 2
fi
package_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
kernel_src=$(realpath "$1")
kernel_build=$(realpath -m "$2")
if [ -e "$kernel_build/.config" ]; then
    echo "Choose a new build directory; an existing .config will not be overwritten."
    exit 2
fi
cd "$kernel_src"
for change in "$package_dir"/patches/*.patch; do
    patch -p1 < "$change"
done
mkdir -p "$kernel_build"
cp "$package_dir/kernel.config" "$kernel_build/.config"
make O="$kernel_build" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
make O="$kernel_build" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 Image
echo "Built $kernel_build/arch/arm64/boot/Image"
