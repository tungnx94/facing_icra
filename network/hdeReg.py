# Vanilla model CNN
import torch
import torch.nn as nn

from hdeNet import HDENet
from extractor import BaseExtractor

SizeDf = [64, 32, 16, 5, 3, 1]
HiddensDF = [3, 64, 64, 128, 128, 256]  # channels
KernelsDF = [5, 5, 3, 3, 3]
PaddingsDF = [2, 2, 1, 1, 0]
StridesDF = [2, 2, 3, 2, 1]


class HDEReg(HDENet):

    def __init__(self, hidNum=256, output_type="reg", device=None, init=True):
        # input size should be [192x192]
        HDENet.__init__(self, device)
        
        self.output_type = output_type
        self.feature = BaseExtractor(hiddens=HiddensDF, kernels=KernelsDF, strides=StridesDF, paddings=PaddingsDF)

        # self.reg = nn.Linear(256, 2)

        if output_type == "reg": # regressor
            self.criterion = nn.MSELoss(reduction='none')  # L2    
            self.reg = nn.Sequential(
                nn.Linear(hidNum, 64),
                nn.ReLU(),
                nn.Linear(64, 2)
            )
        else: # current dirty fix
            self.criterion = nn.CrossEntropyLoss(reduction='none')
            self.reg = nn.Sequential(
                nn.Linear(hidNum, 32),
                nn.ReLU(),
                nn.Linear(32, 8)
            )

        if init:
            self._initialize_weights()
            self.load_to_device()

    def forward(self, x):
        x = x.to(self.device)
        x = self.feature(x).squeeze()
        x = self.reg(x)
        return x

    def loss_label(self, inputs, targets, mean=False):
        inputs = inputs.to(self.device)
        targets = targets.to(self.device)

        outputs = self(inputs)
        loss = self.criterion(outputs, targets)

        if mean:
            loss = torch.mean(loss)
        return loss

if __name__ == '__main__':
    import sys
    sys.path.insert(0, "..")

    import torch.optim as optim
    from utils import get_path
    from dataset import SingleLabelDataset, DataLoader

    net = HDEReg()
    dataset = SingleLabelDataset(
        "duke", path=get_path('DukeMTMC/test/test.csv'), img_size=64)
    dataset.shuffle()
    loader = DataLoader(dataset, batch_size=32)

    optimizer = optim.Adam(net.parameters(), lr=0.03)
    for ind in range(1, 20000):
        sample = loader.next_sample()
        imgseq = sample[0].squeeze()
        labels = sample[1].squeeze()

        loss = net.loss_label(imgseq, labels)
        print loss.item()

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    print "Finished"
