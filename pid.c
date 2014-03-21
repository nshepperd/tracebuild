#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/file.h>
#include <unistd.h>
#include <assert.h>
#include <dlfcn.h>
#include <fcntl.h>

typedef unsigned int uint32;

static char* append(const char* one, const char* two) {
  char* result = malloc(strlen(one) + strlen(two) + 1);
  strcpy(result, one);
  strcat(result, two);
  return result;
}

static uint32 getmyid(char* LOGPATH) {
  uint32 maxid = 1; 		/* start at 1, so we can use 0 as error code */
  char* MAXIDPATH = append(LOGPATH, "/maxid");
  struct stat st_data;
  if(stat(MAXIDPATH, &st_data) == 0) {
    FILE* fp = fopen(MAXIDPATH, "rb");
    assert(fp);
    fread(&maxid, 4, 1, fp);
    fclose(fp);
    /* fprintf(stderr, "\033[41m READ MAXID \033[m %i\n", maxid); */
    maxid++;
  }
 /* else { */
 /*    fprintf(stderr, "\033[41m NO MAXID FILE \033[m\n"); */
 /*  } */

  FILE* fp = fopen(MAXIDPATH, "wb");
  assert(fp != NULL);
  fwrite(&maxid, 4, 1, fp);
  fclose(fp);

  /* fprintf(stderr, "\033[41m WROTE MAXID \033[m %i\n", maxid); */

  free(MAXIDPATH);

  return maxid;
}

static uint32 getid(const char* LOGPATH, uint32 pid) {
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
  }

  free((void*) TABLEPATH);
  return success;
}

static void updateids(char* LOGPATH, uint32 myid) {
  /* idtable :: PID -> UUID */
  char* TABLEPATH = append(LOGPATH, "/idtable");
  FILE* fp = fopen(TABLEPATH, "rb+");
  uint32 kid = 0;
  uint32 mypid = getpid();
  if(fp != NULL) {
    while(!feof(fp)) {
      if(fread(&kid, 4, 1, fp) == 0) {
	break;
      }

      if(kid == mypid) {
	fwrite(&myid, 4, 1, fp);
	fclose(fp);
	free(TABLEPATH);
	return;
      }

      /* otherwise check the next item */
      fseek(fp, 4, SEEK_CUR);
    }
    /* not in the table */
    fwrite(&mypid, 4, 1, fp);
    fwrite(&myid, 4, 1, fp);
    fclose(fp);
  } else {
    /* table didn't exist */
    fp = fopen(TABLEPATH, "wb");
    assert(fp != NULL);
    fwrite(&mypid, 4, 1, fp);
    fwrite(&myid, 4, 1, fp);
    fclose(fp);
  }

  free(TABLEPATH);
  return;
}

typedef struct nstring {
  const char* value;
  uint32 len;
} nstring;

static nstring getcmdline() {
  int pid = getpid();
  char PATH[128];
  sprintf(PATH, "/proc/%i/cmdline", pid);
  FILE* fp = fopen(PATH, "rb");

  char* cmdline = malloc(4096+1);
  int size = fread(cmdline, 1, 4096+1, fp);

  nstring result;
  result.value = cmdline;
  result.len = size;
  return result;
}

static nstring getfwd() {
  char* cwd = getcwd(NULL, 0);
  nstring result;
  result.len = strlen(cwd);
  result.value = cwd;
  return result;
}

static void updateinfo(char* LOGPATH, uint32 myid) {
  nstring cmdline = getcmdline();
  nstring cwd = getfwd();
  uint32 parent_id = getid(LOGPATH, getppid());

  /* if(parent_id == 0) { */
  /*   fprintf(stderr, "unknown ppid, %i\n", getppid()); */
  /*   fprintf(stderr, "my command line: "); */
  /*   fwrite(cmdline.value, 1, cmdline.len, stderr); */
  /*   fprintf(stderr, "\n"); */
  /* } */

  char* INFOPATH = append(LOGPATH, "/info");
  FILE* fp = fopen(INFOPATH, "ab");
  fwrite(&myid, 4, 1, fp);
  fwrite(&parent_id, 4, 1, fp);
  fwrite(&cmdline.len, 4, 1, fp);
  fwrite(cmdline.value, 1, cmdline.len, fp);
  fwrite(&cwd.len, 4, 1, fp);
  fwrite(cwd.value, 1, cwd.len, fp);
  fclose(fp);
  free((void*)cmdline.value);
  free((void*)cwd.value);
  free(INFOPATH);
  /* printf("command line: %s, parent id: %i\n", cmdline.value, parent_id); */
}

static void updatefork(char* LOGPATH, uint32 myid) {
  nstring cmdline = { "fork\0", 5 };
  nstring cwd = getfwd();
  uint32 parent_id = getid(LOGPATH, getppid());
  char* INFOPATH = append(LOGPATH, "/info");
  FILE* fp = fopen(INFOPATH, "ab");
  fwrite(&myid, 4, 1, fp);
  fwrite(&parent_id, 4, 1, fp);
  fwrite(&cmdline.len, 4, 1, fp);
  fwrite(cmdline.value, 1, cmdline.len, fp);
  fwrite(&cwd.len, 4, 1, fp);
  fwrite(cwd.value, 1, cwd.len, fp);
  fclose(fp);
  free((void*)cwd.value);
  free(INFOPATH);
}

void __attribute__ ((constructor))  _pid_init(void) {
  char* LOGPATH = getenv("LOGPATH");
  assert(LOGPATH != NULL);
  assert(sizeof(uint32) == 4);

  char* LOCKPATH = append(LOGPATH, "/lock");
  int fd = open(LOCKPATH, O_RDONLY);
  flock(fd, LOCK_EX);

  uint32 myid = getmyid(LOGPATH);
  updateids(LOGPATH, myid);
  updateinfo(LOGPATH, myid);

  close(fd);
  free(LOCKPATH);
}

pid_t fork() {
  pid_t (*true_fork)() = dlsym(RTLD_NEXT, "fork");
  pid_t result = true_fork();
  if(result == 0) {
    char* LOGPATH = getenv("LOGPATH");
    assert(LOGPATH != NULL);
    assert(sizeof(uint32) == 4);
    mkdir(LOGPATH, 0755);

    char* LOCKPATH = append(LOGPATH, "/lock");
    int fd = open(LOCKPATH, O_RDONLY);
    assert(flock(fd, LOCK_EX) == 0);

    uint32 myid = getmyid(LOGPATH);
    updateids(LOGPATH, myid);
    updatefork(LOGPATH, myid);

    assert(flock(fd, LOCK_UN) == 0);
    close(fd);
  }
  return result;
}
