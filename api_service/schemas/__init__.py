from api_service.schemas.hub_schemas import HubMenuLevelSchema, RenameRequest, HubPositionPatchOut, AddHubLevelScheme, \
    AddHubLevelOutScheme, HubPositionPatch, HubLevelPath, UpdateDeleteImageScheme, UpdatedImageScheme, PathRoutes, \
    OriginHubLevelMap, PathRoute, HubMenuLevelSchema
from api_service.schemas.hubstock_schemas import (HubLoadingData, StockHubItemResult, OriginsPayload,
                                                  HubItemTitlePatch, HubItemsChangePriceRequest,
                                                  HubItemsChangePriceResponse)
from api_service.schemas.comparison_schemas import ComparisonInScheme, ComparisonOutScheme, ParsingLine, \
    ConsentProcessScheme, ParsingHubDiffOut, HubToDiffData, RecalcScheme, RecomputedResult, RecomputedNewPriceLines, \
    ParsingHubDiffItem, UnidentifiedOrigins, UnidentifiedOrigin, HubRoutes, ComparableModel, ComparableUnion, \
    UpdateHubApproveItems, ProductForApproveScheme, UpdateApproveItemResponse
from api_service.schemas.parsing_schemas import ParsingRequest, ParsingLinesIn, ParsingToDiffData, SourceContext, \
    ParsingResultOut, AddAttributesValuesRequest, DependencyImageItem, DependencyOriginImplementation, ImageResponseItem
from api_service.schemas.product_schemas import ProductOriginUpdate, ProductDependencyUpdate, ProductResponse, \
    RecalcPricesRequest, RecalcPricesResponse, ProductOriginCreate, ProductDependencyBatchUpdate, OriginsList, \
    TypeModel, BrandModel, ResolveFeatureModel, ConcurrentAvailable, FetchProductInfoRequest, ImageWithPreview
from api_service.schemas.range_reward_schemas import RewardRangeLineSchema, RewardRangeSchema, \
    RewardRangeResponseSchema, RewardRangeBaseSchema
from api_service.schemas.vsl_schemas import VSLScheme
from api_service.schemas.vendor_schemas import VendorSchema, VslId
from api_service.schemas.service import ServiceImageResponse, ServiceImageCreate, ServiceImageUpdate
from api_service.schemas.attribute_schemas import CreateAttribute, UpdateAttribute, TypesDependenciesResponse, \
    TypeDependencyLink, AttributeBrandRuleLink, TypeAndBrandPayload, ProductFeaturesAttributeOptions, \
    AttributeValueSchema, ModelAttributeValuesSchema, Types, ModelAttributesRequest, ModelAttributesResponse, \
    AttributeModelOptionLink, ParsingResultAttributeResponse, AttributeValueSchema, AttributeOriginValueCheckRequest, \
    AttributeOriginValueCheckResponse, AttributeKeyValueSchema, AttributeKey

from api_service.schemas.formula import FormulaBase, FormulaCreate, FormulaUpdate, FormulaResponse, \
    FormulaPreviewResponse, FormulaPreviewRequest, FormulaValidateRequest, FormulaIdObj

from api_service.schemas.features_schemas import FeaturesDataSet, SetFeaturesHubLevelRequest, SetLevelRoutesResponse, \
    FeaturesElement, FeatureResponseScheme, ProsConsItem, ProsConsItemUpdate, FeatureCategory, \
    UpdateFeatureCategoryRequest, InnerRowRequest, UpdateInnerRowRequest, FeatureIds, TypesAndBrands, \
    CreateFeaturesGlobal, SetFeaturesFormulaRequest, SetFormulaResponse

from api_service.schemas.analytics_schemas import ProductTypeWeightRuleSchema, ProductTypeWeightRuleCreate, \
    ProductTypeWeightRuleDelete, ProductTypeWeightRuleUpdate, ProductTypeWeightRuleSwitch

__all__ = list()

__all__ += ["VendorSchema"]
__all__ += ["VSLScheme", "VslId"]
__all__ += ["ParsingRequest", "ParsingLinesIn", "ParsingToDiffData", "SourceContext", "ParsingResultOut",
            "AddAttributesValuesRequest", "DependencyImageItem", "DependencyOriginImplementation", "ImageResponseItem"]
__all__ += ["RewardRangeLineSchema", "RewardRangeSchema", "RewardRangeResponseSchema", "RewardRangeBaseSchema",
            "AttributeKeyValueSchema", "AttributeKey"]
__all__ += [
    "ProductOriginUpdate", "ProductDependencyUpdate", "ProductResponse", "RecalcPricesRequest", "RecalcPricesResponse",
    "ProductOriginCreate", "ProductDependencyBatchUpdate", "OriginsList", "OriginHubLevelMap", "BrandModel",
    "TypeModel", "ResolveFeatureModel", "ConcurrentAvailable", "FetchProductInfoRequest", "ImageWithPreview"]

__all__ += ["HubMenuLevelSchema", "RenameRequest", "HubPositionPatchOut", "AddHubLevelScheme", "AddHubLevelOutScheme",
            "HubPositionPatch", "HubLevelPath", "UpdateDeleteImageScheme", "UpdatedImageScheme", "PathRoute",
            "HubMenuLevelSchema"]

__all__ += [
    "HubLoadingData", "StockHubItemResult", "OriginsPayload", "HubItemTitlePatch", "HubItemsChangePriceRequest",
    "HubItemsChangePriceResponse"]

__all__ += ["ComparisonInScheme", "ComparisonOutScheme", "ParsingLine", "ConsentProcessScheme",
            "ParsingHubDiffOut", "HubToDiffData", "RecalcScheme", "RecomputedResult", "RecomputedNewPriceLines",
            "ParsingHubDiffItem", "UnidentifiedOrigins", "UnidentifiedOrigin", "HubRoutes", "ComparableModel",
            "ComparableUnion", "UpdateHubApproveItems", "ProductForApproveScheme", "UpdateApproveItemResponse"]

__all__ += ["ServiceImageResponse", "ServiceImageCreate", "ServiceImageUpdate"]

__all__ += ["CreateAttribute", "UpdateAttribute", "TypesDependenciesResponse", "TypeDependencyLink",
            "AttributeBrandRuleLink", "TypeAndBrandPayload", "ProductFeaturesGlobalResponse", "Types",
            "ProductDependenciesKeysValuesScheme", "AttributeKeySchema", "AttributeValueSchema",
            "ProductDependenciesSchema", "AttributeModelOptionLink", "ModelAttributeValuesSchema",
            "ProductFeaturesAttributeOptions", "AttributeValueSchema", "ModelAttributeValuesSchema", "Types",
            "ModelAttributesRequest", "ModelAttributesResponse", "AttributeModelOptionLink",
            "ParsingResultAttributeResponse", "AttributeValueSchema", "AttributeOriginValueCheckRequest",
            "AttributeOriginValueCheckResponse"]

__all__ += ["FormulaBase", "FormulaCreate", "FormulaUpdate", "FormulaResponse", "FormulaPreviewResponse",
            "FormulaPreviewRequest", "FormulaValidateRequest", "FormulaIdObj"]

__all__ += ["FeaturesDataSet", "PathRoutes", "SetFeaturesHubLevelRequest", "SetLevelRoutesResponse", "FeaturesElement",
            "FeatureResponseScheme", "ProsConsItem", "ProsConsItemUpdate", "FeatureCategory",
            "UpdateFeatureCategoryRequest", "InnerRowRequest", "UpdateInnerRowRequest", "FeatureIds", "TypesAndBrands",
            "CreateFeaturesGlobal", "SetFeaturesFormulaRequest", "SetFormulaResponse"]

__all__ += ["ProductTypeWeightRuleSchema", "ProductTypeWeightRuleCreate", "ProductTypeWeightRuleDelete",
            "ProductTypeWeightRuleUpdate", "ProductTypeWeightRuleSwitch"]
