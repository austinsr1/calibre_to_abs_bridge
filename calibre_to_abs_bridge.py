import os
import sys
import errno
import xml.etree.ElementTree as ET
import logging
from fuse import FUSE, Operations


class BookFS(Operations):
    """
    A FUSE filesystem that organizes books based on their metadata.
    """
    def __init__(self, root_dir):
        """
        Initialize the filesystem.

        :param root_dir: The root directory where the books are stored.
        """
        self.root_dir = root_dir
        self.files = {}  # Mapping from virtual paths to actual file paths
        self.directories = set()  # Set of directories in the virtual filesystem
        self.build_file_structure()

    def build_file_structure(self):
        """
        Build the virtual file structure by parsing metadata from the books.
        """
        metadata_files = self.find_metadata_files()
        for metadata_file in metadata_files:
            metadata = self.parse_metadata(metadata_file)
            virtual_book_path = self.get_book_path(metadata)

            # Add the directories to the set
            path_components = virtual_book_path.strip('/').split('/')
            for i in range(1, len(path_components) + 1):
                dir_path = os.path.normpath('/' + '/'.join(path_components[:i]))
                self.directories.add(dir_path)

            # Get the actual book directory (where metadata.opf is located)
            book_dir = os.path.dirname(metadata_file)
            # Map all files in the book directory
            for root, dirs, files in os.walk(book_dir):
                rel_root = os.path.relpath(root, book_dir)
                for file in files:
                    actual_file_path = os.path.join(root, file)
                    rel_file_path = os.path.join(rel_root, file) if rel_root != '.' else file
                    virtual_file_path = os.path.normpath(os.path.join('/', virtual_book_path, rel_file_path))
                    self.files[virtual_file_path] = actual_file_path

                # Add subdirectories to the directories set
                for dir_name in dirs:
                    rel_dir_path = os.path.join(rel_root, dir_name) if rel_root != '.' else dir_name
                    virtual_dir_path = os.path.normpath(os.path.join('/', virtual_book_path, rel_dir_path))
                    self.directories.add(virtual_dir_path)

    def find_metadata_files(self):
        """
        Find all metadata.opf files within the root directory.

        :return: A list of paths to metadata.opf files.
        """
        metadata_files = []
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            if 'metadata.opf' in filenames:
                metadata_files.append(os.path.join(dirpath, 'metadata.opf'))
        return metadata_files

    def parse_metadata(self, file_path):
        """
        Parse metadata from an .opf file.

        :param file_path: Path to the metadata.opf file.
        :return: A dictionary containing metadata.
        """
        ns = {
            'dc': 'http://purl.org/dc/elements/1.1/',
            'opf': 'http://www.idpf.org/2007/opf'
        }
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Extract author
            creator_elem = root.find('.//dc:creator', ns)
            author = creator_elem.text if creator_elem is not None else 'Unknown Author'
            author = self.sanitize_name(author)

            # Extract book title
            title_elem = root.find('.//dc:title', ns)
            book_title = title_elem.text if title_elem is not None else 'Unknown Title'
            book_title = self.sanitize_name(book_title)

            # Extract series information
            series_elem = root.find('.//opf:meta[@name="calibre:series"]', ns)
            series = series_elem.get('content') if series_elem is not None else None
            if series:
                series = self.sanitize_name(series)

            series_index_elem = root.find('.//opf:meta[@name="calibre:series_index"]', ns)
            series_index = series_index_elem.get('content') if series_index_elem is not None else None

            return {
                'author': author,
                'book_title': book_title,
                'series': series,
                'series_index': series_index
            }
        except ET.ParseError as e:
            logging.error(f"Error parsing metadata file {file_path}: {e}")
            return {
                'author': 'Unknown Author',
                'book_title': 'Unknown Title',
                'series': None,
                'series_index': None
            }

    def get_book_path(self, metadata):
        """
        Construct the virtual path for a book based on its metadata.

        :param metadata: A dictionary containing metadata.
        :return: The virtual path for the book.
        """
        author_dir = metadata['author']
        if metadata['series']:
            # Book is part of a series
            series_dir = metadata['series']
            try:
                series_index = int(float(metadata['series_index']))
                book_dir = f"Book {series_index}"
            except (TypeError, ValueError):
                logging.warning(
                    f"Invalid series index '{metadata['series_index']}' for series '{series_dir}'. Using book title instead."
                )
                book_dir = metadata['book_title'] or 'Unknown Book'
            return os.path.join(author_dir, series_dir, book_dir)
        else:
            # Single book
            book_dir = metadata['book_title'] or 'Unknown Book'
            return os.path.join(author_dir, book_dir)

    def sanitize_name(self, name):
        """
        Sanitize a string to be safe for use in file paths.

        :param name: The name to sanitize.
        :return: The sanitized name.
        """
        # Replace any character that is not alphanumeric or safe with '_'
        safe_chars = "-_.() "
        sanitized = ''.join(c if c.isalnum() or c in safe_chars else '_' for c in name)
        # Remove extra whitespace
        sanitized = ' '.join(sanitized.strip().split())
        return sanitized

    # FUSE methods
    def getattr(self, path, fh=None):
        """
        Get file attributes.

        :param path: The path to the file.
        :param fh: File handle (unused).
        :return: A dictionary of file attributes.
        """
        path = os.path.normpath(path)
        if path == '/':
            # Root directory
            mode = 0o755 | 0o040000  # Directory
            return {'st_mode': mode, 'st_nlink': 2}
        elif path in self.files:
            # It's a file
            try:
                mode = 0o644 | 0o100000  # Regular file
                size = os.path.getsize(self.files[path])
                return {'st_mode': mode, 'st_size': size, 'st_nlink': 1}
            except (OSError, IOError) as e:
                logging.error(f"Error getting attributes for file '{path}': {e}")
                raise FileNotFoundError(errno.ENOENT, f"File not found: {path}")
        elif path in self.directories:
            # It's a directory
            mode = 0o755 | 0o040000  # Directory
            return {'st_mode': mode, 'st_nlink': 2}
        else:
            logging.error(f"Path not found in getattr: {path}")
            raise FileNotFoundError(errno.ENOENT, f"Path not found: {path}")

    def readdir(self, path, fh):
        """
        Read a directory.

        :param path: The path to the directory.
        :param fh: File handle (unused).
        :return: A list of directory entries.
        """
        dir_entries = ['.', '..']
        path = os.path.normpath(path)
        if path == '.':
            path = '/'

        # Collect all entries (files and directories) that are immediate children of the current directory
        entries = set()

        # Add directories
        for dir_path in self.directories:
            if os.path.dirname(dir_path) == path:
                entries.add(os.path.basename(dir_path))

        # Add files
        for file_path in self.files:
            if os.path.dirname(file_path) == path:
                entries.add(os.path.basename(file_path))

        dir_entries.extend(entries)
        return dir_entries

    def read(self, path, size, offset, fh):
        """
        Read data from a file.

        :param path: The path to the file.
        :param size: The number of bytes to read.
        :param offset: The offset in the file.
        :param fh: File handle (unused).
        :return: The data read from the file.
        """
        path = os.path.normpath(path)
        if path in self.files:
            try:
                with open(self.files[path], 'rb') as f:
                    f.seek(offset)
                    return f.read(size)
            except (OSError, IOError) as e:
                logging.error(f"Error reading file '{path}': {e}")
                raise OSError(errno.EIO, f"Read error: {path}")
        else:
            logging.error(f"File not found in read: {path}")
            raise FileNotFoundError(errno.ENOENT, f"File not found: {path}")

    def open(self, path, flags):
        """
        Open a file.

        :param path: The path to the file.
        :param flags: Flags indicating access mode.
        :return: File handle (unused).
        """
        path = os.path.normpath(path)
        if path in self.files:
            try:
                # Test if the file can be opened
                fd = os.open(self.files[path], flags)
                os.close(fd)
                return 0
            except (OSError, IOError) as e:
                logging.error(f"Error opening file '{path}': {e}")
                raise OSError(errno.EACCES, f"Cannot open file: {path}")
        else:
            logging.error(f"File not found in open: {path}")
            raise FileNotFoundError(errno.ENOENT, f"File not found: {path}")

    def create(self, path, mode, fi=None):
        """
        Create a file (not allowed).

        :param path: The path to the file.
        :param mode: The mode to create the file with.
        :param fi: File info (unused).
        """
        logging.warning(f"Attempt to create file '{path}' denied.")
        raise OSError(errno.EACCES, 'Permission denied')

    def write(self, path, data, offset, fh):
        """
        Write to a file (not allowed).

        :param path: The path to the file.
        :param data: The data to write.
        :param offset: The offset in the file.
        :param fh: File handle.
        """
        logging.warning(f"Attempt to write to file '{path}' denied.")
        raise OSError(errno.EACCES, 'Permission denied')

    def mkdir(self, path, mode):
        """
        Create a directory (not allowed).

        :param path: The path to the directory.
        :param mode: The mode to create the directory with.
        """
        logging.warning(f"Attempt to create directory '{path}' denied.")
        raise OSError(errno.EACCES, 'Permission denied')

    def rmdir(self, path):
        """
        Remove a directory (not allowed).

        :param path: The path to the directory.
        """
        logging.warning(f"Attempt to remove directory '{path}' denied.")
        raise OSError(errno.EACCES, 'Permission denied')

    def unlink(self, path):
        """
        Remove a file (not allowed).

        :param path: The path to the file.
        """
        logging.warning(f"Attempt to remove file '{path}' denied.")
        raise OSError(errno.EACCES, 'Permission denied')


if __name__ == '__main__':
    import argparse

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='Mount a FUSE filesystem to organize books based on metadata.')
    parser.add_argument('root_dir', help='Root directory containing the books')
    parser.add_argument('mount_point', help='Mount point for the virtual filesystem')
    args = parser.parse_args()

    root_dir = args.root_dir
    mount_point = args.mount_point

    FUSE(
        BookFS(root_dir),
        mount_point,
        nothreads=True,
        foreground=True,
        allow_other=True  # Be cautious with this flag due to security implications
    )
