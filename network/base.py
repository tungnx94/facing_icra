import torch
import torch.nn as nn
#import torch.nn.init as nn.init
from torch.autograd import Variable
import numpy as np
import math
import ipdb

class Conv2d(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride=1, relu=True, same_padding=False, bn=False):
        super(Conv2d, self).__init__()
        padding = int((kernel_size - 1) / 2) if same_padding else 0
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding=padding)
        self.bn = nn.BatchNorm2d(out_channels, eps=0.001, momentum=0, affine=True) if bn else None
        self.relu = nn.ReLU(inplace=True) if relu else None

    def forward(self, x):
        x = self.conv(x)
        if self.bn is not None:
            x = self.bn(x)
        if self.relu is not None:
            x = self.relu(x)
        return x


class FC(nn.Module):
    def __init__(self, in_features, out_features, relu=True):
        super(FC, self).__init__()
        self.fc = nn.Linear(in_features, out_features)
        self.relu = nn.ReLU(inplace=True) if relu else None

    def forward(self, x):
        x = self.fc(x)
        if self.relu is not None:
            x = self.relu(x)
        return x

def save_checkpoint(state, is_best=False, filename='checkpoint.pth.tar'):
    torch.save(state, filename)
    #if is_best:
    #    shutil.copyfile(filename, 'model_best.pth.tar')

def load_checkpoint(filename, model, optimizer=None):
    checkpoint = torch.load(filename)
    start_epoch = checkpoint['epoch']
    #best_prec1 = checkpoint['best_prec1']
    model.load_state_dict(checkpoint['state_dict'])
    if optimizer is not None:
        optimizer.load_state_dict(checkpoint['optimizer'])
    print("=> loaded checkpoint '{}' (epoch {})"
          .format(filename, checkpoint['epoch']))
    return start_epoch, model, optimizer

def load_checkpoint_a2c(filename, actor_model, critic_model=None, actor_optimizer=None, critic_optimizer=None):
    checkpoint = torch.load(filename)
    start_epoch = checkpoint['epoch']
    #best_prec1 = checkpoint['best_prec1']
    #ipdb.set_trace()
    actor_model.load_state_dict(checkpoint['actor_state_dict'])
    if critic_model is not None:
        critic_model.load_state_dict(checkpoint['critic_state_dict'])
    if actor_optimizer is not None:
        actor_optimizer.load_state_dict(checkpoint['actor_optimizer'])
    if critic_optimizer is not None:
        critic_optimizer.load_state_dict(checkpoint['critic_optimizer'])
    print("=> loaded checkpoint '{}' (epoch {})"
          .format(filename, checkpoint['epoch']))
    return start_epoch, actor_model, critic_model, actor_optimizer, critic_optimizer

def save_net(fname, net):
    import h5py
    h5f = h5py.File(fname, mode='w')
    for k, v in net.state_dict().items():
        h5f.create_dataset(k, data=v.cpu().numpy())


def load_net(fname, net):
    import h5py
    h5f = h5py.File(fname, mode='r')
    for k, v in net.state_dict().items():
        param = torch.from_numpy(np.asarray(h5f[k]))
        v.copy_(param)


def load_pretrained_npy(faster_rcnn_model, fname):
    params = np.load(fname).item()
    # vgg16
    vgg16_dict = faster_rcnn_model.rpn.features.state_dict()
    for name, val in vgg16_dict.items():
        # # print name
        # # print val.size()
        # # print param.size()
        if name.find('bn.') >= 0:
            continue
        i, j = int(name[4]), int(name[6]) + 1
        ptype = 'weights' if name[-1] == 't' else 'biases'
        key = 'conv{}_{}'.format(i, j)
        param = torch.from_numpy(params[key][ptype])

        if ptype == 'weights':
            param = param.permute(3, 2, 0, 1)

        val.copy_(param)

    # fc6 fc7
    frcnn_dict = faster_rcnn_model.state_dict()
    pairs = {'fc6.fc': 'fc6', 'fc7.fc': 'fc7'}
    for k, v in pairs.items():
        key = '{}.weight'.format(k)
        param = torch.from_numpy(params[v]['weights']).permute(1, 0)
        frcnn_dict[key].copy_(param)

        key = '{}.bias'.format(k)
        param = torch.from_numpy(params[v]['biases'])
        frcnn_dict[key].copy_(param)


def np_to_variable(x, is_cuda=True, dtype=torch.FloatTensor):
    v = Variable(torch.from_numpy(x).type(dtype))
    if is_cuda:
        v = v.cuda()
    return v

def variable_to_np(x, is_cuda=True):
    x = x.data
    if is_cuda:
        x = x.cpu()
    return x.numpy()

def set_trainable(model, requires_grad):
    for param in model.parameters():
        param.requires_grad = requires_grad


def weights_normal_init(model, dev=0.01):
    if isinstance(model, list):
        for m in model:
            weights_normal_init(m, dev)
    else:
        for m in model.modules():
            if isinstance(m, nn.Conv2d):
                #n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                #m.weight.data.normal_(0, math.sqrt(2. / n))
                #if m.bias is not None:
                #    m.bias.data.zero_()
                #nn.init.xavier_normal_(m)
                m.weight.data.normal_(0.0, dev)
                m.bias.data.zero_()
            elif isinstance(m, nn.Linear):
                #n = m.weight.size(1)
                #m.weight.data.normal_(0, dev)
                #m.bias.data.zero_()
                #nn.init.xavier_normal_(m)
                m.weight.data.normal_(0.0, dev)
                m.bias.data.zero_()

def weights_uniform_init(model, low=0., high=1.):
    if isinstance(model, list):
        for m in model:
            weights_uniform_init(m, dev)
    else:
        for m in model.modules():
            if isinstance(m, nn.Conv2d):
                #n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                #m.weight.data.normal_(0, math.sqrt(2. / n))
                #if m.bias is not None:
                #    m.bias.data.zero_()
                #nn.init.xavier_normal_(m)
                nn.init.uniform_(m, low, high)
                #m.weight.data.normal_(0.0, dev)
                m.bias.data.zero_()
            elif isinstance(m, nn.Linear):
                #n = m.weight.size(1)
                #m.weight.data.normal_(0, dev)
                #m.bias.data.zero_()
                #nn.init.xavier_normal_(m)
                nn.init.uniform_(m, low, high)
                m.bias.data.zero_()

def weights_xavier_init(model, scal=1.):
    if isinstance(model, list):
        for m in model:
            weights_xavier_init(m, dev)
    else:
        for m in model.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(scal / n))
                #if m.bias is not None:
                #    m.bias.data.zero_()
                #nn.init.xavier_normal_(m)
                #nn.init.uniform_(m, low, high)
                #m.weight.data.normal_(0.0, dev)
                m.bias.data.zero_()
            elif isinstance(m, nn.Linear):
                n = m.in_features
                m.weight.data.normal_(0, math.sqrt(scal / n))
                #nn.init.uniform_(m, low, high)
                m.bias.data.zero_()


def clip_gradient(model, clip_norm):
    """Computes a gradient clipping coefficient based on gradient norm."""
    totalnorm = 0
    for p in model.parameters():
        if p.requires_grad:
            modulenorm = p.grad.data.norm()
            totalnorm += modulenorm ** 2
    totalnorm = np.sqrt(totalnorm)

    norm = clip_norm / max(totalnorm, clip_norm)
    for p in model.parameters():
        if p.requires_grad:
            p.grad.mul_(norm)
