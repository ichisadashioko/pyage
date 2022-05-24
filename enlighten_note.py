import time

import enlighten
import tqdm

# counter_1 = enlighten.Counter(total=10)
# counter_1.desc = 'counter_1'
# for x in range(10):
#     time.sleep(1)
#     counter_1.update()

#     counter_2 = enlighten.Counter(total=10)
#     counter_2.desc = 'counter_2'
#     for y in range(10):
#         time.sleep(1)
#         counter_2.update()

pbar1 = tqdm.tqdm(range(10))
pbar1.set_description('pbar1')
for x in pbar1:
    time.sleep(1)

    pbar2 = tqdm.tqdm(range(10))
    pbar2.set_description('pbar2')
    for y in pbar2:
        time.sleep(1)
