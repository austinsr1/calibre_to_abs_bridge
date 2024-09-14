# Calibre to Audiobookshelf Bridge

`calibre_to_abs_bridge.py` is a FUSE-based virtual filesystem that bridges **Calibre** and **Audiobookshelf** by dynamically restructuring your ebook collection to meet Audiobookshelf's directory requirements. It presents your books in a hierarchy organized by author and series, enabling seamless integration with Audiobookshelf without altering your original Calibre library.

## Tested Environment

- **Operating System**: Ubuntu 22.04 LTS

## Prerequisites

Before installing and running the script, ensure that you have the following installed:

- **Python**: Version 3.x
- **FUSE**: Filesystem in Userspace (version 2.x)
- **Python Packages**:
  - `fusepy` (for interfacing with FUSE)
  - Standard libraries (`os`, `sys`, `errno`, `xml`, `logging`, `argparse`)

## Installation

Follow these steps to install the required dependencies and set up the script on Ubuntu 22.04 LTS.

### Step 1: Update Package List

Open a terminal and run:

```bash
sudo apt update
```

### Step 2: Install FUSE and Development Packages

Ubuntu 22.04 comes with FUSE 3.x by default, but `fusepy` requires FUSE 2.x. Install `fuse` and its development libraries:

```bash
sudo apt install -y fuse libfuse2 libfuse-dev
```

**Note**: If `libfuse2` is not installed, you may encounter errors when running the filesystem.

### Step 3: Install Python 3 and Pip

Ensure that Python 3 and `pip` are installed:

```bash
sudo apt install -y python3 python3-pip
```

### Step 4: Install `fusepy` Python Library

Install the `fusepy` library using `pip`:

```bash
pip3 install fusepy
```

### Step 5: Clone the Repository

Clone the repository from GitHub:

```bash
git clone https://github.com/austinsr1/calibre-to-abs-bridge.git
```

### Step 6: Navigate to the Project Directory

```bash
cd calibre-to-abs-bridge
```

## Configuration

### Enable `user_allow_other` in FUSE Configuration

To allow non-root users to access the mounted filesystem with the `allow_other` option, edit the FUSE configuration:

```bash
sudo nano /etc/fuse.conf
```

Uncomment or add the following line:

```
user_allow_other
```

Save and exit the editor (Press `Ctrl+O`, `Enter`, then `Ctrl+X` in Nano).

## Usage

### Step 1: Prepare Directories

- **Calibre Library Directory**: The directory where Calibre stores your ebooks. Each book's directory should contain a `metadata.opf` file, which holds the book's individual metadata.
- **Mount Point**: A directory where the virtual filesystem will be mounted. We'll use `/mnt/abs` as the mount point since Audiobookshelf doesn't have read access to the user's home directory.

Create the mount point directory:

```bash
sudo mkdir -p /mnt/abs
```

Set the permissions so that Audiobookshelf has full access:

```bash
sudo chmod 777 /mnt/abs
```

**Warning**: Using `chmod 777` gives read, write, and execute permissions to all users, which can be a security risk. Ensure that your system's security policies allow for this, or consider more restrictive permissions that still allow Audiobookshelf to function properly.

### Step 2: Run the Script

```bash
python3 calibre_to_abs_bridge.py /path/to/your/calibre/library /mnt/abs
```

Replace `/path/to/your/calibre/library` with the actual path to your Calibre library.

**Note**:

- You might need to run the script with `sudo` if you encounter permission issues:

  ```bash
  sudo python3 calibre_to_abs_bridge.py /path/to/your/calibre/library /mnt/abs
  ```

- Be cautious when running with `sudo` due to security implications.
- Ensure that the user running the script has read permissions for the Calibre library.

### Step 3: Configure Audiobookshelf

In Audiobookshelf:

1. Navigate to **Settings** > **Libraries**.
2. Add a new library or edit an existing one.
3. Set the **Library Path** to your mount point, e.g., `/mnt/abs`.
4. Save the settings and scan the library.

Audiobookshelf will now recognize your books organized according to its required directory structure without duplicating files or altering your Calibre library.

### Example

To view the virtual filesystem:

```bash
cd /mnt/abs
ls
```

You should see directories organized by author, series, and book titles.

## Unmounting

To unmount the filesystem, use:

```bash
fusermount -u /mnt/abs
```

If you ran the script with `sudo`, you might need to unmount with `sudo` as well:

```bash
sudo fusermount -u /mnt/abs
```

## Notes

- **Permissions**:

  - Ensure that Audiobookshelf and the user running the script have the necessary permissions to access `/mnt/abs`.
  - If you encounter permission denied errors, check the permissions of the directories involved.
  - Using `chmod 777` provides full access but can be a security risk. Adjust permissions as needed for your environment.

- **Security**:

  - The `allow_other` option in FUSE lets other users access the mounted filesystem. Understand the security implications before using it.
  - Be cautious when running scripts with `sudo`.

- **Logging**:

  - The script uses Python's `logging` module. Check the console output for logs if you encounter issues.

- **Metadata Requirements**:

  - Each book directory in your Calibre library must contain a `metadata.opf` file, which holds the book's individual metadata used for organizing the filesystem.

## Dependencies

For easy installation of dependencies, you can use the provided `requirements.txt` file.

### Installing via `requirements.txt`

```bash
pip3 install -r requirements.txt
```

Contents of `requirements.txt`:

```
fusepy
```

## License

This project is licensed under the [MIT License](LICENSE).

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch: `git checkout -b feature-name`.
3. Commit your changes: `git commit -am 'Add new feature'`.
4. Push to the branch: `git push origin feature-name`.
5. Open a pull request.
