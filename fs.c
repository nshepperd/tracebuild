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

typedef unsigned int uint32;

static const char* root_path = NULL;
static const char* LOGPATH = NULL;
static const char* log_path = NULL;

static char* append(const char* one, const char* two) {
  char* result = malloc(strlen(one) + strlen(two) + 1);
  strcpy(result, one);
  strcat(result, two);
  return result;
}

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

static void log_access(uint32 id, const char* fname, char rw) {
  uint32 len = strlen(fname);
  FILE* fp = fopen(log_path, "a");
  fwrite(&id, 4, 1, fp);
  fwrite(&rw, 1, 1, fp);
  fwrite(&len, 4, 1, fp);
  fwrite(fname, 1, len, fp);
  fclose(fp);
}

static uint32 getid(uint32 pid) {
  const char* TABLEPATH = append(LOGPATH, "/idtable");
  FILE* fp = fopen(TABLEPATH, "rb");
  uint32 kid = 0;
  uint32 success = 0;
  if(fp != NULL) {
    while(!feof(fp)) {
      if(fread(&kid, 4, 1, fp) == 0) {
	break;
      }

      if(kid == pid) {
	fread(&success, 4, 1, fp);
	break;
      }

      /* otherwise check the next item */
      fseek(fp, 4, SEEK_CUR);
    }
    fclose(fp);
  } else {
    printf("failed to open idtable\n");
  }

  free((void*) TABLEPATH);
  return success;
}

static void maybe_log(const char* fname, char mode) {
  struct fuse_context* context = fuse_get_context();
  uint32 id = getid(context->pid);
  if(id) {
    log_access(id, fname, mode);
  }
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
  to = path_transform(tmp1, to);

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

  struct fuse_context* context = fuse_get_context();
  uint32 id = getid(context->pid);
  if(id) {
    log_access(id, from, 'd');
    log_access(id, to, 'w');
  }

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
  char tmp[4097];
  path_transform(tmp, path);

  int res = open(tmp, fi->flags);
  if (res == -1)
    return -errno;
  close(res);

  switch(fi->flags & 0x03) {
    case O_RDONLY:
      maybe_log(path, 'r');
      break;
    case O_WRONLY:
    case O_RDWR:
      maybe_log(path, 'w');
      break;
    default:
      break;
  }

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

	LOGPATH = getenv("LOGPATH");
	if(LOGPATH == NULL || !strlen(LOGPATH)) {
	  fprintf(stderr, "You need to set LOGPATH.\n");
	  return 1;
	}

	log_path = append(LOGPATH, "/access_log");

	return fuse_main(argc, argv, &xmp_oper, NULL);
}
