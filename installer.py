#!/usr/bin/env python

import curses
import subprocess
import os
import getpass

class PurrInstaller:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.config = {
            "disk": "",
            "partitions": [],
            "mounts": {},
            "timezone": "UTC",
            "locale": "en_US.UTF-8",
            "username": "",
            "user_password": "",
            "wheel": False,
            "root_password": ""
        }
        curses.curs_set(0)
        self.run_installer()

    def run_installer(self):
        """Главная логика инсталлятора"""
        self.config["disk"] = self.select_disk()
        self.run_cfdisk(self.config["disk"])
        self.config["partitions"] = self.select_partitions(self.config["disk"])
        self.config["mounts"] = self.select_mounts(self.config["partitions"])
        self.config["timezone"] = self.select_timezone()
        self.config["locale"] = self.select_locale()
        self.config["username"], self.config["user_password"], self.config["wheel"] = self.setup_user()
        self.config["root_password"] = self.setup_root_password()
        self.show_summary()

        curses.endwin()
        self.generate_script()
        self.run_script()

    def run_cfdisk(self, disk):
        """Запуск cfdisk для разметки диска"""
        curses.endwin()
        subprocess.run(["cfdisk", disk])
        curses.doupdate()

    def select_disk(self):
        """Выбор диска для установки"""
        disks = self.get_disks()
        return self.selection_menu("Select Disk", disks)

    def get_disks(self):
        """Получение списка доступных дисков"""
        return [f"/dev/{d}" for d in subprocess.getoutput("lsblk -d -n -o NAME").split()]

    def select_partitions(self, disk):
        """Выбор разделов после разметки (отбираем только разделы, а не диски)"""
        partitions = []
        try:
            output = subprocess.getoutput(f"lsblk -ln -o NAME,TYPE {disk}")
            for line in output.splitlines():
                name, type_ = line.split()
                if type_ == "part":
                    partitions.append(f"/dev/{name}")
        except Exception as e:
            self.stdscr.addstr(0, 2, f"Error: {str(e)}", curses.A_BOLD)
            self.stdscr.refresh()
            self.stdscr.getch()
        return partitions

    def select_mounts(self, partitions):
        """Выбор точек монтирования (только для разделов)"""
        mounts = {}
        for part in partitions:
            mount = self.text_input(f"Mount point for {part} (leave empty to skip):")
            if mount:
                filesystem = self.selection_menu(f"Select filesystem for {part}", ["ext4", "btrfs", "xfs", "f2fs", "exfat"])
                mounts[part] = {"mount": mount, "filesystem": filesystem}
        return mounts

    def select_timezone(self):
        """Выбор временной зоны"""
        zones = os.listdir("/usr/share/zoneinfo")
        region = self.selection_menu("Select Region", [z for z in zones if os.path.isdir(f"/usr/share/zoneinfo/{z}")])
        cities = os.listdir(f"/usr/share/zoneinfo/{region}")
        return f"{region}/{self.selection_menu(f'Select City ({region})', cities)}"

    def select_locale(self):
        """Выбор локали"""
        locales = []
        with open("/etc/locale.gen", "r") as f:
            for line in f:
                locales.append(line.strip().lstrip("# "))
        selected_locale = self.selection_menu("Select Locale", locales)

        return selected_locale

    def setup_user(self):
        """Настройка первого пользователя"""
        username = self.text_input("Enter username:")
        wheel = self.selection_menu("Add user to wheel group?", ["Yes", "No"]) == "Yes"

        while True:
            password = self.text_input_hidden("Enter password: ")
            confirm = self.text_input_hidden("Confirm password: ")
            if password == confirm:
                break
            self.stdscr.addstr(4, 2, "Passwords do not match. Try again.")
            self.stdscr.refresh()
            self.stdscr.getch()

        return username, password, wheel

    def setup_root_password(self):
        """Установка пароля для root"""
        while True:
            password = self.text_input_hidden("Enter root password: ")
            confirm = self.text_input_hidden("Confirm root password: ")
            if password == confirm:
                break
            self.stdscr.addstr(4, 2, "Passwords do not match. Try again.")
            self.stdscr.refresh()
            self.stdscr.getch()

        return password

    def show_summary(self):
        """Показываем итоговую конфигурацию"""
        self.stdscr.clear()
        mounts = "\n".join([f"{part}: {data['mount']} ({data['filesystem']})" for part, data in self.config["mounts"].items()])
        summary = f"""
        Disk: {self.config["disk"]}
        Partitions: {self.config["partitions"]}
        Mounts: {mounts}
        Timezone: {self.config["timezone"]}
        Locale: {self.config["locale"]}
        User: {self.config["username"]} (Wheel: {'Yes' if self.config["wheel"] else 'No'})
        """
        self.stdscr.addstr(2, 2, summary)
        self.stdscr.addstr(10, 2, "Press any key to start installation...")
        self.stdscr.refresh()
        self.stdscr.getch()

    def selection_menu(self, title, options):
        """Меню выбора с навигацией и поиском"""
        idx = 0
        max_height, _ = self.stdscr.getmaxyx()
        visible_items = max_height - 4
        show_nav = len(options) > visible_items
        offset = 0

        search_query = ""

        while True:
            self.stdscr.clear()
            self.stdscr.addstr(0, 2, title, curses.A_BOLD)

            self.stdscr.addstr(1, 2, f"Search: {search_query}")

            filtered_options = [opt for opt in options if search_query.lower() in opt.lower()]

            end = min(offset + visible_items, len(filtered_options))
            for i, opt in enumerate(filtered_options[offset:end]):
                style = curses.A_REVERSE if i + offset == idx else curses.A_NORMAL
                self.stdscr.addstr(i + 2, 2, opt, style)

            if show_nav:
                self.stdscr.addstr(max_height - 2, 2, "[↑↓] Navigation  [Enter] Select  [Backspace] Delete  [Esc] Exit")

            self.stdscr.refresh()
            key = self.stdscr.getch()

            if key == curses.KEY_UP:
                if idx > 0:
                    idx -= 1
                if idx < offset:
                    offset -= 1
            elif key == curses.KEY_DOWN:
                if idx < len(filtered_options) - 1:
                    idx += 1
                if idx >= offset + visible_items:
                    offset += 1
            elif key == 10 or key == 13:
                return filtered_options[idx]
            elif key == curses.KEY_BACKSPACE:
                search_query = search_query[:-1]
            elif chr(key).isprintable():
                search_query += chr(key)

    def text_input_hidden(self, prompt):
        """Получение текстового ввода с маскировкой (например, для пароля)"""
        curses.noecho()
        self.stdscr.clear()
        self.stdscr.addstr(2, 2, prompt)
        self.stdscr.refresh()

        password = ""
        while True:
            key = self.stdscr.getch()

            if key == 10 or key == 13:
                break
            elif key == curses.KEY_BACKSPACE or key == 127:
                password = password[:-1]
                self.stdscr.move(3, 2)
                self.stdscr.clrtoeol()
                self.stdscr.addstr(3, 2, "*" * len(password))
            elif chr(key).isprintable():
                password += chr(key)
                self.stdscr.move(3, 2)
                self.stdscr.clrtoeol()
                self.stdscr.addstr(3, 2, "*" * len(password))

            self.stdscr.refresh()

        return password

    def text_input(self, prompt):
        """Получение текстового ввода"""
        curses.echo()
        self.stdscr.clear()
        self.stdscr.addstr(2, 2, prompt)
        self.stdscr.refresh()
        input_str = self.stdscr.getstr(3, 2, 20).decode().strip()
        curses.noecho()
        return input_str

    def generate_bash_script(self):
        """Генерация bash скрипта для установки Purr Linux"""
        script = "#!/bin/bash\n\n"

        script += f"if [ -d /sys/firmware/efi ]; then\n"
        script += f"  boot_mode=\"efi\"\n"
        script += f"else\n"
        script += f"  boot_mode=\"bios\"\n"
        script += f"fi\n\n"

        for partition, data in self.config['mounts'].items():
            script += f"mkfs.{data['filesystem']} {partition}\n"

        for partition, data in self.config['mounts'].items():
            script += f"mount {partition} /mnt{data['mount']}\n"

        script += f"echo {self.config['locale']} >> /etc/locale.gen\n"
        script += f"echo LANG={self.config['locale']} > /etc/locale.conf\n"
        script += f"locale-gen\n\n"

        script += f"ln -sf /usr/share/zoneinfo/{self.config['timezone']} /etc/localtime\n"
        script += f"hwclock --systohc\n\n"

        script += f"pacstrap /mnt base linux linux-firmware\n"

        script += f"genfstab -U /mnt >> /mnt/etc/fstab\n"

        script += f"echo 'purr' > /mnt/etc/hostname\n"

        script += f"cp -f /etc/default/grub > /mnt/etc/default/grub\n"
        script += f"cp -f /etc/os-release > /mnt/etc/os-release\n"
        script += f"cp -r /usr/share/pixmaps /mnt/usr/share/\n"

        script += f"arch-chroot /mnt /bin/bash <<EOF\n"

        script += f"useradd -m -s fish -G {'wheel' if self.config['wheel'] else 'users'} {self.config['username']}\n"
        script += f"echo '{self.config['username']}:{self.config['user_password']}' | chpasswd\n"

        script += f"echo 'root:{self.config['root_password']}' | chpasswd\n"

        script += f"if [ \"$boot_mode\" == \"efi\" ]; then\n"
        script += f"  pacman -S --noconfirm grub efibootmgr\n"
        script += f"  grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=arch\n"
        script += f"  grub-mkconfig -o /boot/grub/grub.cfg\n"
        script += f"else\n"
        script += f"  pacman -S --noconfirm grub\n"
        script += f"  grub-install --target=i386-pc --recheck {self.config['disk']}\n"
        script += f"  grub-mkconfig -o /boot/grub/grub.cfg\n"
        script += f"fi\n"

        script += f"pacman -S --noconfirm sddm plasma dolphin arc kate konsole networkmanager opendoas fish\n"
        script += f"echo 'permit persist :wheel' > /etc/doas.conf'\n"

        script += f"EOF\n"

        script += f"echo 'Installation complete! Reboot now.'\n"

        with open("/tmp/install.sh", "w") as f:
            f.write(script)

    def run_script(self):
        subprocess.run(["chmod", "+x", "/tmp/install.sh"])

        process = subprocess.Popen(["/tmp/install.sh"], shell=True)
        process.communicate()

if __name__ == "__main__":
    curses.wrapper(PurrInstaller)
