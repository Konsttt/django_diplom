import random
import string


# Простой генератор пароля (не пригодился в последствии. просто оставил.)
def psw_gen(digits=3, punctuations=2, length=9):
    psw = ''

    for _ in range(digits):
        psw += random.choice(string.digits)

    for _ in range(punctuations):
        psw += random.choice(string.punctuation)

    l = length - digits - punctuations
    for _ in range(l):
        psw += random.choice(string.ascii_letters)

    list1 = list(psw)
    random.shuffle(list1)
    psw = ''.join(list1)

    return psw
