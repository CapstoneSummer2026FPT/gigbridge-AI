import pytest
from app.services.job_posts import is_vietnamese

def test_is_vietnamese_accented():
    assert is_vietnamese("Cần tuyển lập trình viên Nodejs") is True
    assert is_vietnamese("Tuyển dụng designer thiết kế giao diện") is True
    assert is_vietnamese("Chào bạn, tôi cần viết một mô tả công việc") is True

def test_is_vietnamese_unaccented():
    assert is_vietnamese("tuyen lap trinh vien nodejs") is True
    assert is_vietnamese("tuyen dung designer thiet ke giao dien") is True
    assert is_vietnamese("can tuyen gap frontend developer") is True
    assert is_vietnamese("tuyen dev nodejs") is True

def test_is_english():
    assert is_vietnamese("Looking for a React developer with 3 years of experience") is False
    assert is_vietnamese("Need to hire a backend developer for a short term project") is False
    assert is_vietnamese("Job post description for graphic designer") is False
