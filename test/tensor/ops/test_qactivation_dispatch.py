import pytest
import torch
from helpers import assert_similar, random_qactivation, random_tensor

from quanto import QTensor, quantize_activation


@pytest.mark.parametrize("input_shape", [(10,), (1, 10), (10, 32, 32)])
@pytest.mark.parametrize("scalar", [1, 0.5, torch.tensor(0.12)], ids=["int", "float", "tensor"])
def test_qactivation_mul_scalar(input_shape, scalar, device):
    qa = random_qactivation(input_shape, dtype=torch.float32).to(device)
    if isinstance(scalar, torch.Tensor):
        scalar = scalar.to(device)
    qprod = qa * scalar
    assert isinstance(qprod, QTensor)
    prod = qa.dequantize() * scalar
    assert_similar(prod, qprod)
    qprod = scalar * qa
    assert isinstance(qprod, QTensor)
    prod = scalar * qa.dequantize()
    assert_similar(prod, qprod)


@pytest.mark.parametrize("batch_size", [1, 10])
@pytest.mark.parametrize("tokens, embeddings", [(5, 5), (32, 32), (10, 32)])
def test_qactivation_relu(batch_size, tokens, embeddings, device):
    qinputs = random_qactivation((batch_size,) + (tokens, embeddings), dtype=torch.float32).to(device)
    qout = torch.nn.functional.relu(qinputs)
    assert isinstance(qout, QTensor)
    assert torch.equal(qout._data, torch.maximum(qinputs._data, torch.zeros((1,)).to(device)))


@pytest.mark.parametrize("batch_size", [1, 10])
@pytest.mark.parametrize("tokens, embeddings", [(5, 5), (32, 32), (10, 32)])
def test_qactivation_softmax(batch_size, tokens, embeddings, device):
    qinputs = random_qactivation((batch_size,) + (tokens, embeddings), dtype=torch.float32).to(device)
    qout = torch.nn.functional.softmax(qinputs, dim=-1)
    assert isinstance(qout, QTensor)
    assert torch.min(qout.dequantize()) >= 0
    assert torch.max(qout.dequantize()) <= 1


@pytest.mark.parametrize("input_shape", [(10,), (10, 32)])
def test_qactivation_view(input_shape, device):
    qinputs = random_qactivation(input_shape, dtype=torch.float32).to(device)
    qview = qinputs.view((1,) + input_shape)
    assert isinstance(qview, QTensor)


@pytest.mark.parametrize("input_shape", [(10,), (10, 32)])
def test_qactivation_cat(input_shape, device):
    qinputs = random_qactivation(input_shape, dtype=torch.float32).to(device)
    other = random_tensor(input_shape, dtype=torch.float32).to(device)
    # First, quantize other with the same scale
    qother = quantize_activation(other, qtype=qinputs.qtype, scale=qinputs._scale)
    qcat = torch.cat([qinputs, qother])
    assert isinstance(qcat, QTensor)
    assert_similar(torch.cat([qinputs.dequantize(), qother.dequantize()]), qcat)


def test_qactivation_transpose_2d(device):
    input_shape = (4, 6)
    qinputs = random_qactivation(input_shape).to(device)
    qtransposed = qinputs.t()
    assert qtransposed.qtype == qinputs.qtype
    assert qtransposed.shape == input_shape[::-1]
    assert torch.equal(qtransposed.dequantize(), qinputs.dequantize().t())


def test_qactivation_transpose(device):
    input_shape = (10, 32, 64)
    qinputs = random_qactivation(input_shape).to(device)
    qtransposed = torch.transpose(qinputs, 1, 2)
    assert qtransposed.qtype == qinputs.qtype
    assert torch.equal(qtransposed.dequantize(), torch.transpose(qinputs.dequantize(), 1, 2))
