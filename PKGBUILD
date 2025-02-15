pkgname=purrarch-installer
pkgver=1.1
pkgrel=1
pkgdesc="PurrArch installation program"
arch=("any")
url="https://github.com/purrlinux/installer"
license=("MIT")
depends=("python" "ncurses" "util-linux" "arch-install-scripts")
source=("installer.py" "LICENSE")
sha256sums=('398dd61aa24cfe6d142db0cfe00809fa28d150dac3a227c358dda56dce58d019'
            '420adb580620401d1623f2f8dacacd17f303b436c77a5ef8018b6b90c856deb8')

package() {
    install -Dm755 "${srcdir}/installer.py" "${pkgdir}/usr/bin/installer"
    install -Dm644 "${srcdir}/LICENSE" "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
}
