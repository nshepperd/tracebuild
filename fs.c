/*
  FUSE: Filesystem in Userspace
  Copyright (C) 2001-2007  Miklos Szeredi <miklos@szeredi.hu>
  Copyright (C) 2011       Sebastian Pipping <sebastian@pipping.org>

  This program can be distributed under the terms of the GNU GPL.
  See the file COPYING.

  gcc -Wall fusexmp.c `pkg-config fuse --cflags --libs` -o fusexmp
*/

#define FUSE_USE_VERSION 26

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#ifdef linux
/* For pread()/pwrite()/utimensat() */
#define _XOPEN_SOURCE 700
#endif

#define HAVE_SETXATTR
#define HAVE_UTIMENSAT

#include <fuse.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <dirent.h>
#include <errno.h>
#include <sys/time.h>
#ifdef HAVE_SETXATTR
#include <sys/xattr.h>
#endif

static const char* root_path = NULL;
static const char* log_path = NULL;

static const char* path_transform(char* dst, const char* path) {
  const char* nonslash = path;
  while(*nonslash == '/') {
    nonslash++;
  }
  strcpy(dst, root_path);
  strcat(dst, "/");
  strcat(dst, nonslash);
  return dst;
}

static int xmp_getattr(const char *path, struct stat *stbuf)
{
  int res;
  char tmp[4097];
  path = path_transform(tmp, path);

  res = lstat(path, stbuf);
  if (res == -1) {
    return -errno;
  }

  return 0;
}

static int xmp_access(const char *path, int mask)
{
  int res;

  char tmp[4097];
  path = path_transform(tmp, path);

  res = access(path, mask);
  if (res == -1)
    return -errno;

  return 0;
}

static int xmp_readlink(const char *path, char *buf, size_t size)
{
  int res;

  char tmp[4097];
  path = path_transform(tmp, path);

  res = readlink(path, buf, size - 1);
  if (res == -1)
    return -errno;

  buf[res] = '\0';
  return 0;
}


static int xmp_readdir(const char *path, void *buf, fuse_fill_dir_t filler,
		       off_t offset, struct fuse_file_info *fi)
{
  DIR *dp;
  struct dirent *de;

  char tmp[4097];
  path = path_transform(tmp, path);

  (void) offset;
  (void) fi;

  dp = opendir(path);
  if (dp == NULL)
    return -errno;

  while ((de = readdir(dp)) != NULL) {
    struct stat st;
    memset(&st, 0, sizeof(st));
    st.st_ino = de->d_ino;
    st.st_mode = de->d_type << 12;
    if (filler(buf, de->d_name, &st, 0))
      break;
  }

  closedir(dp);
  return 0;
}

static int xmp_mknod(const char *path, mode_t mode, dev_t rdev)
{
  int res;

  char tmp[4097];
  path = path_transform(tmp, path);

  /* On Linux this could just be 'mknod(path, mode, rdev)' but this
     is more portable */
  if (S_ISREG(mode)) {
    res = open(path, O_CREAT | O_EXCL | O_WRONLY, mode);
    if (res >= 0) {
      res = close(res);
    }
  } else if (S_ISFIFO(mode)) {
    res = mkfifo(path, mode);
  } else {
    res = mknod(path, mode, rdev);
  }

  if (res == -1)
    return -errno;

  return 0;
}

static int xmp_mkdir(const char *path, mode_t mode)
{
  int res;

  char tmp[4097];
  path = path_transform(tmp, path);

  res = mkdir(path, mode);
  if (res == -1)
    return -errno;

  return 0;
}

static int xmp_unlink(const char *path)
{
  int res;

  char tmp[4097];
  path = path_transform(tmp, path);

  res = unlink(path);
  if (res == -1)
    return -errno;

  return 0;
}

static int xmp_rmdir(const char *path)
{
  int res;

  char tmp[4097];
  path = path_transform(tmp, path);

  res = rmdir(path);
  if (res == -1)
    return -errno;

  return 0;
}

static int xmp_symlink(const char *from, const char *to)
{
  int res;

  char tmp1[4097];
  from = path_transform(tmp1, from);

  res = symlink(from, to);
  if (res == -1)
    return -errno;

  return 0;
}

static int xmp_rename(const char *from, const char *to)
{
  int res;

  char tmp1[4097];
  char tmp2[4097];
  path_transform(tmp1, from);
  path_transform(tmp2, to);

  res = rename(tmp1, tmp2);
  if (res == -1)
    return -errno;

  // Make 'mv' work
  FILE* fp = fopen(log_path, "a");
  struct fuse_context* context = fuse_get_context();
  fprintf(fp, "(%i, 'read', '%s')\n", getpgid(context->pid), from);
  fprintf(fp, "(%i, 'write', '%s')\n", getpgid(context->pid), to);
  fclose(fp);

  return 0;
}

static int xmp_link(const char *from, const char *to)
{
  int res;

  char tmp1[4097];
  char tmp2[4097];
  from = path_transform(tmp1, from);
  to = path_transform(tmp2, to);

  res = link(from, to);
  if (res == -1)
    return -errno;

  return 0;
}

static int xmp_chmod(const char *path, mode_t mode)
{
  int res;

  char tmp[4097];
  path = path_transform(tmp, path);

  res = chmod(path, mode);
  if (res == -1)
    return -errno;

  return 0;
}

static int xmp_chown(const char *path, uid_t uid, gid_t gid)
{
  int res;

  char tmp[4097];
  path = path_transform(tmp, path);

  res = lchown(path, uid, gid);
  if (res == -1)
    return -errno;

  return 0;
}

static int xmp_truncate(const char *path, off_t size)
{
  int res;

  char tmp[4097];
  path = path_transform(tmp, path);

  res = truncate(path, size);
  if (res == -1)
    return -errno;

  return 0;
}

#ifdef HAVE_UTIMENSAT
static int xmp_utimens(const char *path, const struct timespec ts[2])
{
  int res;

  char tmp[4097];
  path = path_transform(tmp, path);

  /* don't use utime/utimes since they follow symlinks */
  res = utimensat(0, path, ts, AT_SYMLINK_NOFOLLOW);
  if (res == -1)
    return -errno;

  return 0;
}
#endif

static int xmp_open(const char *path, struct fuse_file_info *fi)
{
  int res;

  char tmp[4097];
  path_transform(tmp, path);

  res = open(tmp, fi->flags);
  if (res == -1)
    return -errno;

  FILE* fp = fopen(log_path, "a");
  struct fuse_context* context = fuse_get_context();

  switch(fi->flags & 0x03) {
  case O_RDONLY:
    fprintf(fp, "(%i, 'read', '%s')\n", getpgid(context->pid), path);
    break;
  case O_WRONLY:
  case O_RDWR:
    fprintf(fp, "(%i, 'write', '%s')\n", getpgid(context->pid), path);
    break;
  default:
    break;
  }

  fclose(fp);

  close(res);
  return 0;
}

static int xmp_read(const char *path, char *buf, size_t size, off_t offset,
		    struct fuse_file_info *fi)
{
  int fd;
  int res;

  char tmp[4097];
  path = path_transform(tmp, path);

  (void) fi;
  fd = open(path, O_RDONLY);
  if (fd == -1)
    return -errno;

  res = pread(fd, buf, size, offset);
  if (res == -1)
    res = -errno;

  close(fd);
  return res;
}

static int xmp_write(const char *path, const char *buf, size_t size,
		     off_t offset, struct fuse_file_info *fi)
{
  int fd;
  int res;

  char tmp[4097];
  path = path_transform(tmp, path);

  (void) fi;
  fd = open(path, O_WRONLY);
  if (fd == -1)
    return -errno;

  res = pwrite(fd, buf, size, offset);
  if (res == -1)
    res = -errno;

  close(fd);
  return res;
}

static int xmp_statfs(const char *path, struct statvfs *stbuf)
{
  int res;

  char tmp[4097];
  path = path_transform(tmp, path);

  res = statvfs(path, stbuf);
  if (res == -1)
    return -errno;

  return 0;
}

static int xmp_release(const char *path, struct fuse_file_info *fi)
{
	/* Just a stub.	 This method is optional and can safely be left
	   unimplemented */

	(void) path;
	(void) fi;
	return 0;
}

static int xmp_fsync(const char *path, int isdatasync,
		     struct fuse_file_info *fi)
{
	/* Just a stub.	 This method is optional and can safely be left
	   unimplemented */

	(void) path;
	(void) isdatasync;
	(void) fi;
	return 0;
}

#ifdef HAVE_POSIX_FALLOCATE
static int xmp_fallocate(const char *path, int mode,
			off_t offset, off_t length, struct fuse_file_info *fi)
{
  int fd;
  int res;

  char tmp[4097];
  path = path_transform(tmp, path);

  (void) fi;

  if (mode)
    return -EOPNOTSUPP;

  fd = open(path, O_WRONLY);
  if (fd == -1)
    return -errno;

  res = -posix_fallocate(fd, offset, length);

  close(fd);
  return res;
}
#endif

#ifdef HAVE_SETXATTR
/* xattr operations are optional and can safely be left unimplemented */
static int xmp_setxattr(const char *path, const char *name, const char *value,
			size_t size, int flags)
{
  char tmp[4097];
  path = path_transform(tmp, path);

  int res = lsetxattr(path, name, value, size, flags);
  if (res == -1)
    return -errno;
  return 0;
}

static int xmp_getxattr(const char *path, const char *name, char *value,
			size_t size)
{
  char tmp[4097];
  path = path_transform(tmp, path);

  int res = lgetxattr(path, name, value, size);
  if (res == -1)
    return -errno;
  return res;
}

static int xmp_listxattr(const char *path, char *list, size_t size)
{
  char tmp[4097];
  path = path_transform(tmp, path);

  int res = llistxattr(path, list, size);
  if (res == -1)
    return -errno;
  return res;
}

static int xmp_removexattr(const char *path, const char *name)
{
  char tmp[4097];
  path = path_transform(tmp, path);

  int res = lremovexattr(path, name);
  if (res == -1)
    return -errno;
  return 0;
}
#endif /* HAVE_SETXATTR */

static struct fuse_operations xmp_oper = {
	.getattr	= xmp_getattr,
	.access		= xmp_access,
	.readlink	= xmp_readlink,
	.readdir	= xmp_readdir,
	.mknod		= xmp_mknod,
	.mkdir		= xmp_mkdir,
	.symlink	= xmp_symlink,
	.unlink		= xmp_unlink,
	.rmdir		= xmp_rmdir,
	.rename		= xmp_rename,
	.link		= xmp_link,
	.chmod		= xmp_chmod,
	.chown		= xmp_chown,
	.truncate	= xmp_truncate,
#ifdef HAVE_UTIMENSAT
	.utimens	= xmp_utimens,
#endif
	.open		= xmp_open,
	.read		= xmp_read,
	.write		= xmp_write,
	.statfs		= xmp_statfs,
	.release	= xmp_release,
	.fsync		= xmp_fsync,
#ifdef HAVE_POSIX_FALLOCATE
	.fallocate	= xmp_fallocate,
#endif
#ifdef HAVE_SETXATTR
	.setxattr	= xmp_setxattr,
	.getxattr	= xmp_getxattr,
	.listxattr	= xmp_listxattr,
	.removexattr	= xmp_removexattr,
#endif
};

int main(int argc, char *argv[])
{
	int i;

	umask(0);

	root_path = getenv("FUSE_ROOT");
	if(root_path == NULL || !strlen(root_path)) {
	  root_path = "/";
	}

	// remove trailing slashes
	char* tmp = malloc(strlen(root_path) + 1);
	strcpy(tmp, root_path);
	for(i = strlen(tmp) - 1; i >= 0; i--) {
	  if(tmp[i] == '/') {
	    tmp[i] = 0;
	  } else {
	    break;
	  }
	}
	root_path = tmp;

	printf("%s\n", root_path);

	log_path = getenv("TRACE_LOG_LOCATION");
	if(log_path == NULL || !strlen(log_path)) {
	  fprintf(stderr, "You need to set TRACE_LOG_LOCATION.\n");
	  return 1;
	}

	return fuse_main(argc, argv, &xmp_oper, NULL);
}
