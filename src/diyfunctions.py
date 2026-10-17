import torch


def real(tensor):
    return torch.real(tensor) + 0j
def imag(tensor):
    tensor += 0j
    return torch.imag(tensor) * 1j
def abs(tensor):
    return torch.abs(tensor) + 0j
def angle(tensor):
    return torch.angle(tensor) + 0j
def square(tensor):
    return tensor * tensor
def cubic(tensor):
    return tensor * tensor * tensor
def parallel(tensor):
    return (tensor * tensor)/(tensor + tensor - 1 )
