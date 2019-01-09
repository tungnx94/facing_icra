import os
import torch

class HDENet(torch.nn.Module):

    def __init__(self, device=None):
        super(HDENet, self).__init__()
        self.countTrain = 0
        self.device = device

        if device is None:  #select default if not specified
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else: 
            self.device = torch.device(device)

    def new_variable(self, tensor, **kwargs):
        var = torch.autograd.Variable(tensor, **kwargs) # deprecated
        if self.device == torch.device("cuda"):
            var = var.cuda()
        return var

    def load_to_device(self):
        if self.device == torch.device("cuda"):
            self.cuda()

    def load_from_npz(self, file):
        model_dict = self.state_dict()

        preTrainDict = torch.load(file)
        preTrainDict = {k: v for k, v in preTrainDict.items() if k in model_dict}

        model_dict.update(preTrainDict)
        self.load_state_dict(model_dict)
        
        """
        print 'preTrainDict:',preTrainDict.keys()
        print 'modelDict:',model_dict.keys()
    
        for item in preTrainDict:
            print '  Load pretrained layer: ', item
        for item in model_dict:
            print '  Model layer: ',item
        """

    def load_pretrained(self, file):
        # file needs to point to a relative path
        modelname = os.path.splitext(os.path.basename(file))[0]
        self.countTrain = int(modelname.split('_')[-1])
        self.load_from_npz(file)

        self.load_to_device()

    def _initialize_weights(self):
        pass