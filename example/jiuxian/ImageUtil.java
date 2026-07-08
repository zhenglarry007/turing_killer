package com.newxtc.msg.util;

import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

import javax.imageio.ImageIO;

import org.openqa.selenium.Dimension;
import org.openqa.selenium.WebElement;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.alibaba.fastjson.JSONArray;

public class ImageUtil {
	public static final HashMap<String, String> mFileTypes = new HashMap<String, String>();
	private static Logger logger = LoggerFactory.getLogger(ImageUtil.class);

	static {
		mFileTypes.put("FFD8FF", "jpg");
		mFileTypes.put("89504E47", "png");
		mFileTypes.put("47494638", "gif");
		mFileTypes.put("49492A00", "tif");
		mFileTypes.put("424D", "bmp");
	}

	/**
	 * 图片覆盖（覆盖图压缩到width*height大小，覆盖到底图上）
	 *
	 * @param baseBufferedImage
	 *            底图
	 * @param coverBufferedImage
	 *            覆盖图
	 * @param x
	 *            起始x轴
	 * @param y
	 *            起始y轴
	 */
	public static void overlayImage(BufferedImage baseBufferedImage, BufferedImage coverBufferedImage, int x, int y) {
		// 创建Graphics2D对象，用在底图对象上绘图
		Graphics2D g2d = baseBufferedImage.createGraphics();
		// 绘制
		g2d.drawImage(coverBufferedImage, x, y, coverBufferedImage.getWidth(), coverBufferedImage.getHeight(), null);
		// 释放图形上下文使用的系统资源
		g2d.dispose();
	}

	/**
	 * 
	 * @param bgElement
	 * @param bigBytes
	 * @return [bigWidth,dimenWidth]
	 */
	public static Integer[] getPicWidth(WebElement bgElement, byte[] bigBytes) {
		// 获取显示尺寸和图片物理尺寸
		try {
			ByteArrayInputStream bgObj = new ByteArrayInputStream(bigBytes);
			BufferedImage bgBI = ImageIO.read(bgObj);
			int bigWidth = bgBI.getWidth();
			Dimension dimenSize = bgElement.getSize();
			int dimenWidth = dimenSize.getWidth();
			System.out.println("      |-bigWidth=" + bigWidth + ",dimenWidth=" + dimenWidth);
			return new Integer[] { bigWidth, dimenWidth };
		} catch (Exception e) {
			return null;
		}
	}

	public static byte[] overlayBig(byte[] titleBytes, byte[] bigBytes) {
		return overlayBig(titleBytes, bigBytes, false);
	}

	public static byte[] overlayBig(byte[] titleBytes, byte[] bigBytes, boolean titleWhite) {
		try {
			ByteArrayInputStream titleObj = new ByteArrayInputStream(titleBytes);
			BufferedImage titleBi = ImageIO.read(titleObj);
			int titleHeight = titleBi.getHeight();

			ByteArrayInputStream bgObj = new ByteArrayInputStream(bigBytes);
			BufferedImage bgBI = ImageIO.read(bgObj);

			BufferedImage targetImage = new BufferedImage(bgBI.getWidth(), bgBI.getHeight() + titleHeight, BufferedImage.TYPE_INT_ARGB);

			overlayImage(targetImage, bgBI, 0, 0);
			if (titleWhite) {
				// 创建白色背景的title图像
				int titleWidth = titleBi.getWidth();
				BufferedImage whiteBgTitle = new BufferedImage(titleWidth, titleHeight, BufferedImage.TYPE_INT_RGB);
				java.awt.Graphics2D g2d = whiteBgTitle.createGraphics();
				g2d.setColor(java.awt.Color.WHITE);
				g2d.fillRect(0, 0, titleWidth, titleHeight);
				g2d.drawImage(titleBi, 0, 0, null);
				g2d.dispose();
				overlayImage(targetImage, whiteBgTitle, 0, bgBI.getHeight());
			} else
				overlayImage(targetImage, titleBi, 0, bgBI.getHeight());

			ByteArrayOutputStream out = new ByteArrayOutputStream();
			ImageIO.write(targetImage, "png", out);
			out.flush();
			byte[] picBytes = out.toByteArray();
			return picBytes;
		} catch (Exception e) {
			return null;
		}
	}

	/**
	 * 输入 N 个图片，将N个图片横向拼接， 找出最大的高，合并N个图片的宽，构建拼接的底图，将N个图片按顺序覆盖到底图上
	 * 
	 * @param labelList
	 *            图片字节数组列表
	 * @param scale
	 *            缩放比例（例如：1.0保持原始大小，0.5缩放一半）
	 * @return 拼接后的图片字节数组
	 */
	public static byte[] getOverlayImage(List<byte[]> labelList) {
		if (labelList == null || labelList.isEmpty()) {
			return null;
		}
		List<BufferedImage> images = new ArrayList<>();
		int totalWidth = 0;
		int maxHeight = 0;
		// 将字节数组转换为BufferedImage并计算总宽度和最大高度
		BufferedImage img;
		for (byte[] imageData : labelList) {
			try {
				img = ImageIO.read(new ByteArrayInputStream(imageData));
				if (img == null) {
					continue;
				}
				images.add(img);
				totalWidth += img.getWidth();
				maxHeight = Math.max(maxHeight, img.getHeight());

			} catch (IOException e) {
				e.printStackTrace();
			}
		}

		if (images.isEmpty()) {
			return null;
		}

		// 创建底图
		BufferedImage targetImage = new BufferedImage(totalWidth, maxHeight, BufferedImage.TYPE_INT_RGB);
		Graphics2D g2d = targetImage.createGraphics();
		// 关键：先填充白色背景，避免黑色背景
		g2d.setColor(Color.WHITE);
		g2d.fillRect(0, 0, totalWidth, maxHeight);

		// 横向拼接图片
		int currentX = 0;
		for (BufferedImage img2 : images) {
			g2d.drawImage(img2, currentX, 0, null);
			currentX += img2.getWidth();
		}

		g2d.dispose();

		// 将BufferedImage转换为byte[]
		try (ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
			ImageIO.write(targetImage, "jpg", baos);
			return baos.toByteArray();
		} catch (IOException e) {
			e.printStackTrace();
			return null;
		}
	}

	/**
	 * x0, y0, width, height
	 * 
	 * @param originalImage
	 * @param bbox
	 * @return
	 */
	public static byte[] getSubByte(BufferedImage originalImage, JSONArray bbox) {
		try {
			// 将 bigBytes 转换为 BufferedImage
			// BufferedImage originalImage = ImageIO.read(new
			// ByteArrayInputStream(bigBytes));
			// 切割图片
			int x0 = bbox.getIntValue(0);
			int y0 = bbox.getIntValue(1);
			int width = bbox.getIntValue(2) - x0;
			int height = bbox.getIntValue(3) - y0;
			BufferedImage subImage = originalImage.getSubimage(x0, y0, width, height);

			// 将切割后的图片转换为 byte[]
			ByteArrayOutputStream baos = new ByteArrayOutputStream();
			ImageIO.write(subImage, "jpg", baos); // 可以根据实际格式调整（如 "jpg"）
			byte[] imageBytes = baos.toByteArray();
			return imageBytes;
		} catch (Exception e) {
			System.out.print("getSubImage() " + e.toString());
			return null;
		}
	}

	/**
	 * 
	 * @param originalImage
	 * @param bbox
	 * @return
	 */
	public static byte[] getSubByte(BufferedImage originalImage, Integer[] bbox) {
		return getSubByte(originalImage, bbox, "jpg");
	}

	/**
	 * 
	 * @param originalImage
	 * @param bbox
	 * @param picType
	 * @return
	 */
	public static byte[] getSubByte(BufferedImage originalImage, Integer[] bbox, String picType) {
		int x0 = -1, y0 = -1, width = -1, height = -1;
		try {
			// 将 bigBytes 转换为 BufferedImage
			// BufferedImage originalImage = ImageIO.read(new
			// ByteArrayInputStream(bigBytes));
			// 切割图片
			x0 = bbox[0];
			y0 = bbox[1];
			width = bbox[2] - x0;
			height = bbox[3] - y0;
			BufferedImage subImage = originalImage.getSubimage(x0, y0, width, height);

			// 将切割后的图片转换为 byte[]
			ByteArrayOutputStream baos = new ByteArrayOutputStream();
			ImageIO.write(subImage, picType, baos); // 可以根据实际格式调整（如 "jpg"）
			byte[] imageBytes = baos.toByteArray();
			return imageBytes;
		} catch (Exception e) {
			System.out.println("getSubImage() x0=" + x0 + ", y0=" + y0 + ", width=" + width + ", height=" + height + ",e=" + e.toString());
			return null;
		}
	}

	public static byte[] picCut(BufferedImage fullBI, int startX, int width) {
		try {
			BufferedImage N1 = fullBI.getSubimage(startX, 0, width, fullBI.getHeight());
			ByteArrayOutputStream out = new ByteArrayOutputStream();
			ImageIO.write(N1, "png", out);
			byte[] mBytes = out.toByteArray();
			return mBytes;
		} catch (Exception e) {
			return null;
		}
	}

	/**
	 * 将图片裁剪为2行4列共8个小图片
	 * 
	 * @param imageBytes
	 *            原始图片字节数组
	 * @param formatName
	 *            图片格式（如"jpg", "png"）
	 * @return 包含8个小图片字节数组的List（按行优先顺序）
	 * @throws IOException
	 */
	public static List<byte[]> cropImageTo8Parts(BufferedImage originalImage, String formatName) throws IOException {
		List<byte[]> result = new ArrayList<>(8);

		int width = originalImage.getWidth();
		int height = originalImage.getHeight();

		// 计算每个小图的宽度和高度
		int subImageWidth = width / 4; // 4列
		int subImageHeight = height / 2; // 2行

		// 按行优先顺序裁剪（先第一行从左到右，再第二行从左到右）
		BufferedImage subImage;
		ByteArrayOutputStream baos;
		for (int row = 0; row < 2; row++) {
			for (int col = 0; col < 4; col++) {
				// 计算裁剪区域
				int x = col * subImageWidth;
				int y = row * subImageHeight;

				// 确保最后一列/行包含剩余像素
				int w = (col == 3) ? width - x : subImageWidth;
				int h = (row == 1) ? height - y : subImageHeight;

				// 裁剪图片
				subImage = originalImage.getSubimage(x, y, w, h);

				// 转换为字节数组
				baos = new ByteArrayOutputStream();
				ImageIO.write(subImage, formatName, baos);
				result.add(baos.toByteArray());
			}
		}

		return result;
	}

}
