from fastapi import APIRouter, Depends, HTTPException
from typing import List
from user import UserCreate, User

router = APIRouter()
