from typing import Optional

from pydantic import BaseModel

from api_service.schemas import VSLSchemeWithBrands


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


class VendorApiSearchBase(BaseModel):
    vendor_id: int
    category_id: int
    title: Optional[str] = None
    id_path: Optional[str] = None
    search_params: Optional[dict] = None


class AddVendorApiSearch(VendorApiSearchBase):
    pass


class VendorApiSearchObj(VendorApiSearchBase):
    id: int | None


class ApiSearchAlreadyExists(VendorApiSearchObj):
    status: bool


class ProductsFromApiResponse(BaseModel):
    status: str
    total: int
    exec_time: float
    already_exists: ApiSearchAlreadyExists
    products: list[ProductFromApi]


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


class ApiSearchVSLResponse(BaseModel):
    status: bool
    all_VSL: list[VSLSchemeWithBrands]
    linked_VSL: Optional[list[VSLSchemeWithBrands]]


class UpdateLinesFromApi(BaseModel):
    linked_VSL: list[VSLSchemeWithBrands]
    raw_products: list[ProductFromApi]
