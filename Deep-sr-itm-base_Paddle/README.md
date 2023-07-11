# deep_sr_itm_paddle

Paper: Deep SR-ITM: Joint Learning of Super-Resolution and Inverse Tone-Mapping for 4K UHD HDR Applications.

[Paper](https://paperswithcode.com/paper/deep-sr-itm-joint-learning-of-super)

作者: Soo Ye Kim等

Paddle 复现版本

## 数据集

https://pan.baidu.com/s/1OSLVoBioyen-zjvLmhbe2g

提取码: 2me9

## 训练模型

链接：https://pan.baidu.com/s/19fx-CqYr8jvS-4rMHZkqYg?pwd=hh66 
提取码：hh66

## 训练步骤

### train 

```bash
python train.py -opt config/train/train_sritm.yml
```

```
多卡仅需
​```bash
python -m paddle.distributed.launch train.py --launcher fleet -opt config_file_path
```

## 测试步骤

```bash
python test.py -opt config/test/test_sritm.yml
```

## 复现指标

|        | PSNR  |
| ------ | ----- |
| Paddle | 34.85 |

注：因显存限制，测试结果为测试图片降采样到1080p的结果