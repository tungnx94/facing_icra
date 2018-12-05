# This file is modified from train_ed_semi_cls.py
# Change the classification model to regression model
import cv2
import random
import torch

import torch.nn as nn
import torch.optim as optim
import numpy as np
import matplotlib.pyplot as plt

from os.path import join as joinPathPath
from torch.autograd import Variable
from dataset.generalData import DataLoader

from utils.data import groupPlot
from network EncoderReg_Pred

from dataset import FolderUnlabelData

from facingDroneLabelData import FacingDroneLabelDataset
from facingLabelData import FacingLabelDataset

UseGPU = torch.cuda.is_available()

exp_prefix = '20_2_'

OutDir = 'resimg'
DataDir = 'data_facing' # save folder for snapshot
DatasetDir = '/home/wenshan/datasets'

ModelName = 'models_facing/' + exp_prefix + 'pred_reg'
ModelFile = joinPath(OutDir, ModelName.split('/')[-1] + '.png')

LossFile = joinPath(DataDir, exp_prefix + 'lossplot.npy')
ValLossFile = joinPath(DataDir, exp_prefix + 'vallossplot.npy')
LabelLossFile = joinPath(DataDir, exp_prefix + 'unlabellossplot.npy')
UnlabelLossFile = joinPath(DataDir, exp_prefix + 'labellossplot.npy')

TrainFolder1 = joinPath(DatasetDir, 'droneData/label') #
TrainFolder2 = joinPath(DatasetDir, 'facing/facing_img_coco') #
AnnoFolder2 = joinPath(DatasetDir, 'facing/facing_anno') #
ValFolder = joinPath(DatasetDir, 'droneData/val') #
UnlabelFolder = joinPath(DatasetDir, 'dirimg') 

LR = 0.01
Lamb = 5.0
TrainBatch = 32
UnlabelBatch = 32  # sequence length
ValBatch = 100
TrainStep = 10000
ShowIter = 50
SnapShot = 2000
TrainLayers = 0

Hiddens = [3, 16, 32, 32, 64, 64, 128, 256]
Kernels = [4, 4, 4, 4, 4, 4, 3]
Paddings = [1, 1, 1, 1, 1, 1, 0]
Strides = [2, 2, 2, 2, 2, 2, 1]


def visualize(lossplot, labellossplot, unlabellossplot, vallossplot, unlabellossplot):
    labellossplot = np.array(labellossplot).reshape((-1, 1)).mean(axis=1)
    vallossplot = np.array(vallossplot)

    ax1 = plt.subplot(131)
    ax1.plot(labellossplot)
    ax1.plot(vallossplot)
    ax1.grid()

    lossplot = np.array(lossplot).reshape((-1, 1)).mean(axis=1)
    ax2 = plt.subplot(132)
    ax2.plot(lossplot)
    ax2.grid()

    unlabellossplot = np.array(unlabellossplot)
    gpunlabelx, gpunlabely = groupPlot(
        range(len(unlabellossplot)), unlabellossplot)

    ax3 = plt.subplot(133)
    ax3.plot(unlabellossplot)
    ax3.plot(gpunlabelx, gpunlabely, color='y')
    ax3.grid()

    plt.savefig(ModelFile)
    plt.show()


def train_label_unlabel(encoderReg, sample, unlabel_sample, regOptimizer, criterion, lamb):
    """ train one step """
    # label
    inputImgs = sample['img']
    labels = sample['label']

    inputState = Variable(inputImgs, requires_grad=True)
    targetreg = Variable(labels, requires_grad=False)

    # unlabel
    imgseq = unlabel_sample.squeeze()
    inputState_unlabel = Variable(imgseq, requires_grad=True)

    if UseGPU:
        inputState = inputState.cuda()
        targetreg = targetreg.cuda()
        inputState_unlabel = inputState_unlabel.cuda()

    # forward pass
    output, _, _ = encoderReg(inputState)
    
    output_unlabel, encode, pred = encoderReg(inputState_unlabel)
    pred_target = encode[UnlabelBatch / 2:, :].detach()

    loss_label = criterion(output, targetreg)
    loss_pred = criterion(pred, pred_target)

    loss = loss_label + loss_pred * Lamb

    # backpropagate
    regOptimizer.zero_grad()
    loss.backward()
    regOptimizer.step()

    return loss_label.data[0], loss_pred.data[0], loss.data[0]


def test_label(val_sample, encoderReg, criterion, batchnum=1):
    """ validate on labeled dataset """
    inputImgs = val_sample['img']
    labels = val_sample['label']
    inputState = Variable(inputImgs, requires_grad=False)
    targetreg = Variable(labels, requires_grad=False)

    if UseGPU:
        inputState = inputState.cuda()
        targetreg = targetreg.cuda()

    output, _, _ = encoderReg(inputState)
    loss = criterion(output, targetreg)

    return loss.data[0]

"""
encode the input using pretrained model
print 'load pretrained...'
#preTrainModel = 'models_facing/8_13_ed_reg_46000.pkl'
#preTrainModel = 'models_facing/3_5_ed_cls_10000.pkl'
#preTrainModel = 'models_facing/1_2_encoder_decoder_facing_leaky_50000.pkl'
preTrainModel = 'models_facing/13_1_ed_reg_100000.pkl'
encoderReg=loadPretrain(encoderReg,preTrainModel)
"""
def save_snapshot(model, label_loss, unlabel_loss, total_loss, val_loss):
    torch.save(model.state_dict(), ModelName + '_' + str(ind) + '.pkl')

    np.save(LossFile, total_loss)
    np.save(ValLossFile, val_loss)
    np.save(LabelLossFile, label_loss)
    np.save(UnlabelLossFile, unlabel_loss)

def main():
    # Encoder model
    encoderReg = EncoderReg_Pred(
        Hiddens, Kernels, Strides, Paddings, actfunc='leaky', rnnHidNum=128)
    encoderReg.cuda()

    paramlist = list(encoderReg.parameters())
    regOptimizer = optim.SGD(paramlist[-TrainLayers:], lr=LR, momentum=0.9)
    # regOptimizer = optim.Adam(paramlist[-TrainLayers:], lr = lr)

    criterion = nn.MSELoss()

    # Datasets
    imgdataset = FacingDroneLabelDataset(imgdir=TrainFolder1, data_aug=True)
    imgdataset2 = FacingLabelDataset(annodir=AnnoFolder2, imgdir=TrainFolder2, data_aug=True)

    unlabelset = FolderUnlabelDataset(imgdir=UnlabelFolder, batch=UnlabelBatch, data_aug=True, extend=True)

    valset = FacingDroneLabelDataset(imgdir=ValFolder)
    
    # Dataloaders
    dataloader = DataLoader(imgdataset, batch_size=TrainBatch, num_workers=2)
    dataloader2 = DataLoader(imgdataset2, batch_size=TrainBatch, num_workers=2)
    valloader = DataLoader(valset, batch_size=ValBatch,
                           num_workers=2, shuffle=False)
    unlabelloader = DataLoader(unlabelset, num_workers=2)

    # Loss history
    lossplot = []
    labellossplot = []
    unlabellossplot = []
    vallossplot = []

    # Train
    val_loss = 0.0
    for ind in range(1, TrainStep + 1):
        # load next samples
        if ind % 2 == 0:
            sample = dataloader.next_sample()
        else sample = dataloader2.next_sample()

        unlabel_sample = unlabelloader.next_sample()

        # run one training step
        label_loss, unlabel_loss, total_loss = train_label_unlabel(
            encoderReg, sample, unlabel_sample, regOptimizer, criterion, Lamb)

        labellossplot.append(label_loss)
        unlabellossplot.append(unlabel_loss)
        lossplot.append(total_loss)

        # Validate on test set
        if ind % ShowIter == 0:
            val_losses = [test_label(val_sample, encoderReg, criterion)
                          for val_sample in valloader]
            val_loss = sum(val_losses) / len(val_losses)  # take average

            vallossplot.append(val_loss)

        print('[%s %d] loss: %.5f, label-loss: %.5f, val-loss: %.5f, unlabel-loss: %.5f' %
              (exp_prefix[:-1], ind, total_loss, label_loss, val_loss, unlabel_loss))

        if ind % SnapShot == 0:  # Save model + loss
            save_shapshot(encoderReg, labellossplot, unlabellossplot, lossplot, vallossplot)

    visualize(lossplot, labellossplot, unlabellossplot, vallossplot)

if __name__ == "__main__":
    main()