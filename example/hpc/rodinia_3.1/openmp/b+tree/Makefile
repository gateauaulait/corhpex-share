C_C = $(CCC) $(MODE)
OMP_LIB = -fopenmp
OMP_FLAG = -fopenmp

# ========================================================================================================================================================================================================200
#	EXECUTABLES (LINK OBJECTS TOGETHER INTO BINARY)
# ========================================================================================================================================================================================================200

b+tree.out:	./main.o \
		./kernel/kernel_cpu.o \
		./kernel/kernel_cpu_2.o \
		./util/timer/timer.o \
		./util/num/num.o
	$(C_C)	./main.o \
			./kernel/kernel_cpu.o \
			./kernel/kernel_cpu_2.o \
			./util/timer/timer.o \
			./util/num/num.o \
			-lm \
			$(OMP_LIB) \
                        -o b+tree.out
# ========================================================================================================================================================================================================200
#	OBJECTS (COMPILE SOURCE FILES INTO OBJECTS)
# ========================================================================================================================================================================================================200

# ======================================================================================================================================================150
#	MAIN FUNCTION
# ======================================================================================================================================================150

main.o:	./common.h \
		./main.h \
		./main.c
	$(C_C)	./main.c \
			-c \
			-o ./main.o 

# ======================================================================================================================================================150
#	KERNELS
# ======================================================================================================================================================150

./kernel/kernel_cpu.o:	./common.h \
						./kernel/kernel_cpu.h \
						./kernel/kernel_cpu.c
	$(C_C)	./kernel/kernel_cpu.c \
			-c \
			-o ./kernel/kernel_cpu.o \
			$(OMP_FLAG)

./kernel/kernel_cpu_2.o:./common.h \
						./kernel/kernel_cpu_2.h \
						./kernel/kernel_cpu_2.c
	$(C_C)	./kernel/kernel_cpu_2.c \
			-c \
			-o ./kernel/kernel_cpu_2.o \
			$(OMP_FLAG)

# ======================================================================================================================================================150
#	UTILITIES
# ======================================================================================================================================================150

./util/timer/timer.o:	./common.h \
						./util/timer/timer.h \
						./util/timer/timer.c
	$(C_C)	./util/timer/timer.c \
			-c \
			-o ./util/timer/timer.o 

./util/num/num.o:	./common.h \
					./util/num/num.h \
					./util/num/num.c
	$(C_C)	./util/num/num.c \
			-c \
			-o ./util/num/num.o 

# ======================================================================================================================================================150
#	END
# ======================================================================================================================================================150

# ========================================================================================================================================================================================================200
#	DELETE
# ========================================================================================================================================================================================================200

clean:
	rm	-f *.o *.out \
		./kernel/*.o \
		./util/timer/*.o \
		./util/num/*.o \
                output.txt

# ========================================================================================================================================================================================================200
#	END
# ========================================================================================================================================================================================================200
