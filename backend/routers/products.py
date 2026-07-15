from fastapi import APIRouter, HTTPException, Query


router = APIRouter(prefix="/products", tags=["products"])
