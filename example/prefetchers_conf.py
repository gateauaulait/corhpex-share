import subprocess
from itertools import product

# default values of registers
# reg_0x1A4 = 0
# reg_0x1320 = 0x108837ea470906c4
# reg_0x1321 = 0x171122147800

MLC_LLC_STREAMER_BIT = 0
L1_NLP_BIT = 2
L1_IPP_BIT = 3
L1_NPP_BIT = 4
AMP_BIT = 5
LLC_STREAMER_BIT = 43
L2_NLP_BIT = 40

MLC_LLC_STREAMER_ON = ~(1 << MLC_LLC_STREAMER_BIT)
MLC_LLC_STREAMER_OFF = (1 << MLC_LLC_STREAMER_BIT)
MLC_LLC_STREAMER=[MLC_LLC_STREAMER_ON, MLC_LLC_STREAMER_OFF]

L1_NLP_ON = ~(1 << L1_NLP_BIT)
L1_NLP_OFF = (1 << L1_NLP_BIT)
L1_NLP=[L1_NLP_ON, L1_NLP_OFF]

L1_IPP_ON = ~(1 << L1_IPP_BIT)
L1_IPP_OFF = (1 << L1_IPP_BIT)
L1_IPP=[L1_IPP_ON, L1_IPP_OFF]

L1_NPP_ON = ~(1 << L1_NPP_BIT)
L1_NPP_OFF = (1 << L1_NPP_BIT)
L1_NPP = [L1_NPP_ON, L1_NPP_OFF]

AMP_ON = ~(1 << AMP_BIT)
AMP_OFF = (1 << AMP_BIT)
AMP=[AMP_ON, AMP_OFF]

LLC_STREAMER_ON = ~(1 << LLC_STREAMER_BIT)
LLC_STREAMER_OFF = (1 << LLC_STREAMER_BIT)
LLC_STREAMER=[LLC_STREAMER_ON, LLC_STREAMER_OFF]

L2_NLP_ON = ~(1 << L2_NLP_BIT)
L2_NLP_OFF = (1 << L2_NLP_BIT)
L2_NLP=[L2_NLP_ON, L2_NLP_OFF]


# get configuration only for 0x1A4 register prefetchers
def get_all_reg_0x1A4_conf():
    reg_0x1A4_conf = []
    # Pair feature masks with their names
    features = [
        ("MLC_LLC_STREAMER", MLC_LLC_STREAMER),
        ("L1_NLP", L1_NLP),
        ("L1_IPP", L1_IPP),
        ("L1_NPP", L1_NPP),
        ("AMP", AMP)
    ]
    # Generate all combinations of on/off states
    for state_combo in product(*[f[1] for f in features]):
        reg = 0
        for val in state_combo:
            reg = reg & val if val < 0 else reg | val
        reg_0x1A4_conf.append(f"0x{reg:02x}")

    # print(f"Binary values: {[bin(int(x, 16))[2:].zfill(8) for x in reg_0x1A4_conf]}")
    print(reg_0x1A4_conf)
    return reg_0x1A4_conf


# get configuration only for 0x1320 register prefetcher(ON/OFF)
def get_reg_0x1320_conf():
  reg_0x1320 = 0x108837ea470906c4
  reg_0x1320_conf=[]
  for n in range(len(LLC_STREAMER)):
    if n == 0:
      reg_0x1320 = reg_0x1320 & LLC_STREAMER[n]
    else:
      reg_0x1320 = reg_0x1320 | LLC_STREAMER[n]
    reg_0x1320_conf.append(f"0x{reg_0x1320:02x}")
#   print(f"Binary values: {[bin(int(x, 16))[2:].zfill(8) for x in reg_0x1320_conf]}")  
  print(reg_0x1320_conf)
  return reg_0x1320_conf

# get configuration only for 0x1321 register prefetchers
def get_reg_0x1321_conf():
  reg_0x1321 = 0x171122147800
  reg_0x1321_conf=[]
  for o in range(len(L2_NLP)):
    if o == 0:
      reg_0x1321 = reg_0x1321 & L2_NLP[o]
    else:
      reg_0x1321 = reg_0x1321 | L2_NLP[o]
    reg_0x1321_conf.append(f"0x{reg_0x1321:02x}")
#   print(f"Binary values: {[bin(int(x, 16))[2:].zfill(8) for x in reg_0x1321_conf]}")  
  print(reg_0x1321_conf)
  return reg_0x1321_conf


def main():

  print("0x1A4 register prefetchers (ON/OFF): ")
  get_all_reg_0x1A4_conf()

  print("0x1320 register prefetcher (ON/OFF): ")
  get_reg_0x1320_conf()

  print("0x1321 register prefetcher (ON/OFF): ")
  get_reg_0x1321_conf()

  
if __name__ == "__main__":
  main()