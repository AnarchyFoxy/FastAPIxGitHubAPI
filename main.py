from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import List
import httpx


app = FastAPI()

