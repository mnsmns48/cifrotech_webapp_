from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    login: str
    password: str


class ProductFromApi(BaseModel):
    productCode: Optional[str] = None
    name: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[float] = None
    amount: Optional[float] = None
    delivery: Optional[str] = None


class ProductsFromApiResponse(BaseModel):
    status: str
    total: int
    exec_time: float
    already_exists: bool
    products: list[ProductFromApi]


class AddVendorApiSearch(BaseModel):
    vendor_id: int
    category_id: int
    title: str
    id_path: str
    search_params: Optional[dict] = None


class VendorApiSearchResponse(BaseModel):
    status: str
    id: int
    vendor_id: int
    category_id: int
    title: str
    id_path: str
    search_params: dict | None = None


class DeleteVendorApiSearch(BaseModel):
    vendor_id: int
    category_id: int


class VendorApiSearchDeleteResponse(DeleteVendorApiSearch):
    status: str
    deleted_id: int | None = None
