import random

new_arr =[]
for i in range(6):
    random_int = random.randint(0,100)
    new_arr.append(random_int)

n= 7
print(f'nilai awal sebuah array \n{new_arr}\n nilai n adalah {n}')
print('---------------------------')
def odd_even(n):
    return 'genap' if n%2==0 else 'ganjil'

print(f'nilai n adalah {odd_even(n)}')
print('--------------------------- ')


arr = [11,5,6,1,15,7,20,8,4]
def sorting(n):
    
    for i in range(0, len(n)+1):
        for j in range (i ,len(n)):
            if n[i] > n[j]:
                n[i],n[j] = n[j], n[i]
                
    return n

print(f'array setelah diurutkan {sorting(new_arr)}')



def max_val(n):
    potition = 0
    for i  in range(0,len(n)):
        if n[i]>potition:
            potition=n[i]
        else:
            continue
    return potition
print(f'nilai tertinggi adalah : {max_val(new_arr)}')