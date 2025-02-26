'''ResNet in PyTorch.

For Pre-activation ResNet, see 'preact_resnet.py'.

Reference:
[1] Kaiming He, Xiangyu Zhang, Shaoqing Ren, Jian Sun
    Deep Residual Learning for Image Recognition. arXiv:1512.03385
'''
import torch
import torch.nn as nn
import torch.nn.functional as F
from models.normalize import Normalize
import math
from torch.autograd import Variable

class MySequential(nn.Sequential):
    def forward(self, x, adv):
        for module in self._modules.values():
            x = module(x, adv=adv)
        return x
    
class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, in_planes, planes, stride=1, bn_adv_flag=False, bn_adv_momentum=0.01):
        super(BasicBlock, self).__init__()
        
        self.bn_adv_flag = bn_adv_flag
        self.bn_adv_momentum = bn_adv_momentum
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        if self.bn_adv_flag:
            self.bn1_adv = nn.BatchNorm2d(planes, momentum = self.bn_adv_momentum)
            
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=1, padding=1, bias=False)
        
        self.bn2 = nn.BatchNorm2d(planes)
        if self.bn_adv_flag:
            self.bn2_adv = nn.BatchNorm2d(planes, momentum = self.bn_adv_momentum)
            
        self.shortcut = nn.Sequential()
        self.shortcut_bn = None
        self.shortcut_bn_adv = None
        if stride != 1 or in_planes != self.expansion*planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, self.expansion*planes, kernel_size=1, stride=stride, bias=False),
            )
            self.shortcut_bn = nn.BatchNorm2d(self.expansion*planes)
            if self.bn_adv_flag:
                self.shortcut_bn_adv = nn.BatchNorm2d(self.expansion*planes, momentum = self.bn_adv_momentum)

    def forward(self, x, adv=False):
        if adv and self.bn_adv_flag:
            out = F.relu(self.bn1_adv(self.conv1(x)))
            out = self.conv2(out)
            out = self.bn2_adv(out)
            if self.shortcut_bn_adv:
                out += self.shortcut_bn_adv(self.shortcut(x))
            else:
                out += self.shortcut(x)
        else:
            out = F.relu(self.bn1(self.conv1(x)))
            out = self.conv2(out)
            out = self.bn2(out)
            if self.shortcut_bn:
                out += self.shortcut_bn(self.shortcut(x))
            else:
                out += self.shortcut(x)
                
        out = F.relu(out)
        return out


class Bottleneck(nn.Module):
    expansion = 4

    def __init__(self, in_planes, planes, stride=1, bn_adv_flag=False, bn_adv_momentum = 0.01):
        super(Bottleneck, self).__init__()
        
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=1, bias=False)
        self.bn_adv_flag = bn_adv_flag
         
        self.bn_adv_momentum = bn_adv_momentum
        self.bn1 = nn.BatchNorm2d(planes)
        if self.bn_adv_flag:
            self.bn1_adv = nn.BatchNorm2d(planes, momentum = self.bn_adv_momentum)
            
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        
        self.bn2 = nn.BatchNorm2d(planes)
        self.bn2 = nn.BatchNorm2d(planes)
        if self.bn_adv_flag:
            self.bn2_adv = nn.BatchNorm2d(planes, momentum = self.bn_adv_momentum)
            
        self.conv3 = nn.Conv2d(planes, self.expansion*planes, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(self.expansion*planes)
        if self.bn_adv_flag:
            self.bn3_adv = nn.BatchNorm2d(self.expansion*planes, momentum = self.bn_adv_momentum)

        self.shortcut = nn.Sequential()
        self.shortcut_bn_adv = None
        self.shortcut_bn = None
        if stride != 1 or in_planes != self.expansion*planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, self.expansion*planes, kernel_size=1, stride=stride, bias=False),          
            )
            self.shortcut_bn = nn.BatchNorm2d(self.expansion*planes)
            if self.bn_adv_flag:
                self.shortcut_bn_adv = nn.BatchNorm2d(self.expansion*planes, momentum = self.bn_adv_momentum)

    def forward(self, x, adv=False):
        
        if adv and self.bn_adv_flag:
            out = F.relu(self.bn1_adv(self.conv1(x)))
            out = F.relu(self.bn2_adv(self.conv2(out)))
            out = self.bn3_adv(self.conv3(out))
            if self.shortcut_bn_adv:
                out += self.shortcut_bn_adv(self.shortcut(x))
            else:
                out += self.shortcut(x)
        else:
            
            out = F.relu(self.bn1(self.conv1(x)))
            out = F.relu(self.bn2(self.conv2(out)))
            out = self.bn3(self.conv3(out))
            if self.shortcut_bn:
                out += self.shortcut_bn(self.shortcut(x))
            else:
                out += self.shortcut(x)
            
        out = F.relu(out)
        return out


class resnet_cifar(nn.Module):
    def __init__(self, block, num_blocks, pool_len =4, low_dim=128, bn_adv_flag=False, bn_adv_momentum = 0.01):
        super(resnet_cifar, self).__init__()
        self.in_planes = 64
        self.bn_adv_flag = bn_adv_flag
        
        self.bn_adv_momentum = bn_adv_momentum
        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn_adv_flag = bn_adv_flag
        
        self.bn1 = nn.BatchNorm2d(64)
        if bn_adv_flag:
            self.bn1_adv = nn.BatchNorm2d(64, momentum = self.bn_adv_momentum)
        
            
        self.layer1 = self._make_layer(block, 64, num_blocks[0], stride=1, bn_adv_flag = self.bn_adv_flag, bn_adv_momentum = bn_adv_momentum)
        self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2, bn_adv_flag = self.bn_adv_flag, bn_adv_momentum = bn_adv_momentum)
        self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2, bn_adv_flag = self.bn_adv_flag, bn_adv_momentum = bn_adv_momentum)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=2, bn_adv_flag = self.bn_adv_flag, bn_adv_momentum = bn_adv_momentum)
        self.linear = nn.Linear(512*block.expansion, low_dim)
        self.l2norm = Normalize(2)
        self.pool_len = pool_len
        # for m in self.modules():
            # if isinstance(m, nn.Conv2d):
                # n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                # m.weight.data.normal_(0, math.sqrt(2. / n))
            # elif isinstance(m, nn.BatchNorm2d):
                # m.weight.data.fill_(1)
                # m.bias.data.zero_()

    def _make_layer(self, block, planes, num_blocks, stride, bn_adv_flag=False, bn_adv_momentum=0.1):
        strides = [stride] + [1]*(num_blocks-1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, stride, bn_adv_flag=bn_adv_flag, bn_adv_momentum = bn_adv_momentum))
            self.in_planes = planes * block.expansion
        return MySequential(*layers)
        #return layers
        
    def forward(self, x, adv = False):
        if adv and self.bn_adv_flag:
            out = F.relu(self.bn1_adv(self.conv1(x)))
        else:
            out = F.relu(self.bn1(self.conv1(x)))
        
        out = self.layer1(out, adv=adv)
        out = self.layer2(out, adv=adv)
        out = self.layer3(out, adv=adv)
        out = self.layer4(out, adv=adv)
       
        out = F.avg_pool2d(out, self.pool_len)
        out = out.view(out.size(0), -1)
        out = self.linear(out)
        out = self.l2norm(out)
        return out


class resnet_cifar_supervised(nn.Module):
    def __init__(self, block, num_blocks, pool_len=4, low_dim=128, bn_adv_flag=False, bn_adv_momentum = 0.01, num_classes=100):
        super(resnet_cifar_supervised, self).__init__()
        self.in_planes = 64
        self.bn_adv_flag = bn_adv_flag
        
        self.bn_adv_momentum = bn_adv_momentum
        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn_adv_flag = bn_adv_flag
        
        self.bn1 = nn.BatchNorm2d(64)
        if bn_adv_flag:
            self.bn1_adv = nn.BatchNorm2d(64, momentum = self.bn_adv_momentum)
        
            
        self.layer1 = self._make_layer(block, 64, num_blocks[0], stride=1, bn_adv_flag = self.bn_adv_flag, bn_adv_momentum = bn_adv_momentum)
        self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2, bn_adv_flag = self.bn_adv_flag, bn_adv_momentum = bn_adv_momentum)
        self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2, bn_adv_flag = self.bn_adv_flag, bn_adv_momentum = bn_adv_momentum)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=2, bn_adv_flag = self.bn_adv_flag, bn_adv_momentum = bn_adv_momentum)
        self.linear = nn.Linear(512*block.expansion, low_dim)
        # self.l2norm = Normalize(2)
        self.pool_len = pool_len
        self.clf_head = nn.Linear(low_dim, num_classes)

    def _make_layer(self, block, planes, num_blocks, stride, bn_adv_flag=False, bn_adv_momentum=0.1):
        strides = [stride] + [1]*(num_blocks-1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, stride, bn_adv_flag=bn_adv_flag, bn_adv_momentum = bn_adv_momentum))
            self.in_planes = planes * block.expansion
        return MySequential(*layers)
        #return layers
        
    def forward(self, x, adv = False):
        if adv and self.bn_adv_flag:
            out = F.relu(self.bn1_adv(self.conv1(x)))
        else:
            out = F.relu(self.bn1(self.conv1(x)))
        
        out = self.layer1(out, adv=adv)
        out = self.layer2(out, adv=adv)
        out = self.layer3(out, adv=adv)
        out = self.layer4(out, adv=adv)
       
        out = F.avg_pool2d(out, self.pool_len)
        out = out.view(out.size(0), -1)
        out = self.linear(out)

        out = self.clf_head(out)
        
        return out


def resnet18_cifar(pool_len = 4, low_dim=128, bn_adv_flag=False, bn_adv_momentum= 0.01):
    return resnet_cifar(BasicBlock, [2,2,2,2], pool_len, low_dim, bn_adv_flag=bn_adv_flag, bn_adv_momentum=bn_adv_momentum)

def resnet34_cifar(pool_len = 4, low_dim=128, bn_adv_flag=False, bn_adv_momentum= 0.01):
    return resnet_cifar(BasicBlock, [3,4,6,3], pool_len, low_dim, bn_adv_flag=bn_adv_flag)

def resnet50_cifar(pool_len = 4, low_dim=128, bn_adv_flag=False, bn_adv_momentum= 0.01):
    return resnet_cifar(Bottleneck, [3,4,6,3], pool_len, low_dim, bn_adv_flag=bn_adv_flag)

def resnet101_cifar(pool_len = 4, low_dim=128, bn_adv_flag=False, bn_adv_momentum= 0.01):
    return resnet_cifar(Bottleneck, [3,4,23,3], pool_len, low_dim, bn_adv_flag=bn_adv_flag)

def resnet152_cifar(pool_len = 4, low_dim=128, bn_adv_flag=False, bn_adv_momentum= 0.01):
    return resnet_cifar(Bottleneck, [3,8,36,3], pool_len, low_dim, bn_adv_flag=bn_adv_flag)



def resnet18_cifar_supervised(pool_len = 4, low_dim=128, bn_adv_flag=False, bn_adv_momentum= 0.01):
    return resnet_cifar_supervised(BasicBlock, [2,2,2,2], pool_len, low_dim, bn_adv_flag=bn_adv_flag, bn_adv_momentum=bn_adv_momentum)

def resnet34_cifar_supervised(pool_len = 4, low_dim=128, bn_adv_flag=False, bn_adv_momentum= 0.01):
    return resnet_cifar_supervised(BasicBlock, [3,4,6,3], pool_len, low_dim, bn_adv_flag=bn_adv_flag)

def resnet50_cifar_supervised(pool_len = 4, low_dim=128, bn_adv_flag=False, bn_adv_momentum= 0.01):
    return resnet_cifar_supervised(Bottleneck, [3,4,6,3], pool_len, low_dim, bn_adv_flag=bn_adv_flag)

def resnet101_cifar_supervised(pool_len = 4, low_dim=128, bn_adv_flag=False, bn_adv_momentum= 0.01):
    return resnet_cifar_supervised(Bottleneck, [3,4,23,3], pool_len, low_dim, bn_adv_flag=bn_adv_flag)

def resnet152_cifar(pool_len = 4, low_dim=128, bn_adv_flag=False, bn_adv_momentum= 0.01):
    return resnet_cifar_supervised(Bottleneck, [3,8,36,3], pool_len, low_dim, bn_adv_flag=bn_adv_flag)



