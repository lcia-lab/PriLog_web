# -*- coding: utf-8 -*-
import cv2
import numpy as np
from PIL import Image
import sys

if __name__ == '__main__':
    # 検証ソース
    fileList = [
        "damage_data",
        "damage_menu",
        "menu",
        "timer_sec",
        "UB_name",
    ]

    for i, v in enumerate(fileList):
        print("model/{}.npy".format(v))
        ld = np.load("model/{}.npy".format(v))
        path = 'model/decode/' + v + "_{}"+ '.png'

        if v in ["damage_data", "timer_sec", "UB_name"]:
            for i in range(len(ld)):
                ret = cv2.imwrite(path.format(i), ld[i])
        else :
            ret = cv2.imwrite(path.format(0), ld)

