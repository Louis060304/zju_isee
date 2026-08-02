import torch
from torch import nn
import torch.nn.functional as F


class VisionTransformer(nn.Module):
    """
    Vision Transformer (ViT) model for image classification.
    
    Args:
        img_size (int): Input image height and width (assumed square).
        patch_size (int): Size of the patches to be extracted from the image.
        in_chans (int): Number of input image channels.
        num_classes (int): Number of classes for classification.
        embed_dim (int): Dimensionality of the token embeddings.
        depth (int): Number of Transformer encoder layers.
        num_heads (int): Number of attention heads in the Transformer encoder.
        dim_feedforward (int): Dimensionality of the feedforward network model.
        dropout (float): Dropout probability.
    """
    def __init__(self,
                img_size: int = 28,
                patch_size: int = 7,  # Changed from 16 to 7 for 28x28 images (4x4 patches)
                in_chans: int = 1,
                num_classes: int = 10,
                embed_dim: int = 256,
                depth: int = 4,
                num_heads: int = 8,
                dim_feedforward: int = 1024,
                dropout: float = 0.1):
        super().__init__()
        
        # 1. Image Tokenization (Patch Embedding)
        self.patch_embed = nn.Conv2d(in_chans, embed_dim, kernel_size=patch_size, stride=patch_size)
        num_patches = (img_size // patch_size) ** 2

        # 2. Class Token & Positional Embedding
        self.cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))
        self.pos_embed = nn.Parameter(torch.zeros(1, num_patches + 1, embed_dim))
        self.pos_drop = nn.Dropout(p=dropout)

        # 3. Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            activation='gelu',
            batch_first=True,
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=depth)

        # 4. Classification Head
        self.norm = nn.LayerNorm(embed_dim)
        self.head = nn.Sequential(
            nn.Linear(embed_dim, embed_dim),
            nn.ReLU(),
            nn.Linear(embed_dim, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass of the ViT model.
        
        Args:
            x (torch.Tensor): Input images of shape (B, C, H, W).
            
        Returns:
            torch.Tensor: Classification logits of shape (B, num_classes).
        """
        B = x.shape[0]

        # --- Tokenization ---
        x = self.patch_embed(x)                     # (B, embed_dim, H/P, W/P)
        x = x.flatten(2).transpose(1, 2)            # (B, num_patches, embed_dim)

        # --- Concatenate CLS Token ---
        cls_tokens = self.cls_token.expand(B, -1, -1) 
        x = torch.cat((cls_tokens, x), dim=1)       # (B, num_patches + 1, embed_dim)

        # --- Add Positional Encoding ---
        x = x + self.pos_embed
        x = self.pos_drop(x)

        # --- Transformer Encoding ---
        x = self.transformer_encoder(x)             # (B, num_patches + 1, embed_dim)

        # --- Classification ---
        cls_token_final = x[:, 0]                   # 提取第一个位置的 [CLS] token
        cls_token_final = self.norm(cls_token_final)
        
        return self.head(cls_token_final)


class CCT(nn.Module):
    """
    Compact Convolutional Transformer (CCT) model.
    Replaces standard patch embedding with a Convolutional Tokenizer, 
    and uses Sequence Pooling instead of a [CLS] token.
    """
    def __init__(self,
                img_size: int = 28,
                in_chans: int = 1,
                num_classes: int = 10,
                embed_dim: int = 256,
                depth: int = 4,
                num_heads: int = 8,
                dim_feedforward: int = 1024,
                dropout: float = 0.1):
        super().__init__()

        """
        TODO 1: Convolutional Tokenizer
            CCT 使用CNN卷积代替了 ViT 简单的 Patch Embedding。
            请在此处使用 nn.Sequential 完善卷积分词器。
            结构建议：
            1. Conv2d (输入通道数为 in_chans，输出为 64，kernel_size=3, stride=1, padding=1)
            2. ReLU
            3. MaxPool2d (kernel_size=3, stride=2, padding=1)
            4. Conv2d (输入通道数为 64，输出为 embed_dim，kernel_size=3, stride=1, padding=1)
            5. ReLU
            6. MaxPool2d (kernel_size=3, stride=2, padding=1)
        """
        # 1. Convolutional Tokenizer
        self.tokenizer = nn.Sequential(
            # 完全参照TODO1给出的参数编写
            # TODO1
            nn.Conv2d(in_chans, 64, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1),
            nn.Conv2d(64, embed_dim, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        )

        # Calculate number of patches after two 2x2 max poolings
        self.num_patches = (img_size // 4) ** 2

        # 2. Positional Embedding
        self.pos_embed = nn.Parameter(torch.zeros(1, self.num_patches, embed_dim))
        self.pos_drop = nn.Dropout(p=dropout)

        # 3. Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            activation='gelu',
            batch_first=True,
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=depth)

        """
        TODO 2: Sequence Pooling (参数定义)
            CCT 舍弃了 [CLS] token，转而使用 Sequence Pooling 来提取全局特征。
            请在此处定义一个线性层 (Linear)，用于计算每个 token 的重要性权重。
            输入特征维度应为 embed_dim，输出特征维度应为 1。
        """
        # 4. Sequence Pooling (Attention-based pooling)
        self.attention_pool = nn.Linear(embed_dim, 1) #TODO2

        # 5. Classification Head
        self.norm = nn.LayerNorm(embed_dim)
        self.head = nn.Linear(embed_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass of the CCT model.
        
        Args:
            x (torch.Tensor): Input images of shape (B, C, H, W).
            
        Returns:
            torch.Tensor: Classification logits of shape (B, num_classes).
        """
        # --- Convolutional Tokenization ---
        x = self.tokenizer(x)                       # (B, embed_dim, 7, 7)
        x = x.flatten(2).transpose(1, 2)            # (B, 49, embed_dim)

        # --- Add Positional Encoding ---
        x = x + self.pos_embed
        x = self.pos_drop(x)

        # --- Transformer Encoding ---
        x = self.transformer_encoder(x)             # (B, 49, embed_dim)

        # --- Sequence Pooling ---
        # 计算每个序列单元的注意力权重
        attn_weights = self.attention_pool(x)       # (B, 49, 1)
        attn_weights = F.softmax(attn_weights, dim=1)
        
        # 将权重应用于序列进行加权求和
        # (B, 1, 49) @ (B, 49, embed_dim) -> (B, 1, embed_dim) -> (B, embed_dim)
        x = torch.matmul(attn_weights.transpose(1, 2), x).squeeze(1)

        # --- Classification ---
        x = self.norm(x)
        return self.head(x)


class MSELoss(nn.Module):
    def __init__(self):
        super(MSELoss, self).__init__()
        self.l2 = nn.MSELoss()

    def forward(self, estimate, target):
        # 获取device确保target tensor和estimate tensor在同一device上
        device = estimate.device
        # 从estimate tensor获取类别的总数
        n = estimate.size(1)
        # 将target转换为one-hot编码形式
        target = F.one_hot(target, num_classes=n).float().to(device)
        # 计算MSE loss
        return self.l2(estimate, target)