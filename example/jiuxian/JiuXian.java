package com.newxtc.send.selenium.wordDet;

import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.util.ArrayList;
import java.util.List;

import javax.imageio.ImageIO;

import org.apache.commons.io.FileUtils;
import org.openqa.selenium.By;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;

import com.alibaba.fastjson.JSONObject;
import com.newxtc.chrome.ChromeUtil;
import com.newxtc.msg.entity.RetEntity;
import com.newxtc.msg.ocr.sp.OcrClientDddd;
import com.newxtc.msg.util.GenChecksumUtil;
import com.newxtc.msg.util.GetImage;
import com.newxtc.msg.util.ImageUtil;
import com.newxtc.msg.util.PropertiesUtil;
import com.newxtc.selenium.ActionMove;
import com.newxtc.selenium.ResultWrite;
import com.newxtc.selenium.RobotMove;
import com.newxtc.send.SendDriverApi;
import com.newxtc.send.SendTestUtil;

/**
 * 酒仙网
 *
 */
public class JiuXian implements SendDriverApi {
	private static String dataPath = System.getProperty("java.io.tmpdir") + "JiuXian" + File.separator;

	private OcrClientDddd ddddOcr = new OcrClientDddd();
	private String INDEX_URL = "https://login.jiuxian.com/login.htm";

	@Override
	public RetEntity send(WebDriver driver, String areaCode, String phone) {
		RetEntity retEntity = new RetEntity();
		try {
			driver.get(INDEX_URL);

			// 1 短信登录
			WebElement tabElement = ChromeUtil.waitElement(driver, By.xpath("//a[text()='手机动态密码登录']"), 10);
			tabElement.click();

			// 2 输入手机号
			WebElement phoneElement = ChromeUtil.waitElement(driver, By.name("phone"), 1);
			phoneElement.sendKeys(phone);

			ChromeUtil.waitElement(driver, By.id("captchaImage_mobile"), 10);
			byte[] titleBytes = GetImage.callJsById(driver, "captchaImage_mobile");

			BufferedImage titleImage = (titleBytes != null) ? ImageIO.read(new ByteArrayInputStream(titleBytes)) : null;
			byte[] smallByte = (titleImage != null) ? ImageUtil.getSubByte(titleImage, new Integer[] { 91, 0, 168, titleImage.getHeight() }) : null;
			int smallLen = (smallByte != null) ? smallByte.length : -1;
			if (smallLen < 100) {
				retEntity.setMsg("smallLen:" + smallLen);
				return retEntity;
			}
			String titleOrg = ddddOcr.getImgCode(smallByte);

			String title = (titleOrg != null) ? titleOrg.replaceAll("[^\u4e00-\u9fa5]", "") : null;
			if (title == null || title.length() != 3) {
				System.out.println("titleOrg=" + titleOrg + "->" + title);
				return retEntity;
			}
			File ocrFile = new File(dataPath + "title" + File.separator + title + ".png");
			FileUtils.writeByteArrayToFile(ocrFile, smallByte);
			// ddddOcr.saveFile(this.getClass().getSimpleName(), title, smallByte);

			// 3 依次点击
			WebElement findElement = driver.findElement(By.id("captchaImage_mobile"));
			findElement.click();

			byte[] bigBytes = GetImage.callJsById(driver, "captchaImage2_mobile");
			int bigLen = (bigBytes != null) ? bigBytes.length : -1;
			if (bigLen < 100) {
				retEntity.setMsg("bigLen:" + bigLen);
				return retEntity;
			}
			long begin = System.currentTimeMillis();
			// extRate 扩展比例
			// 0.2 -> 54.4%
			// 0.15 -> 
			JSONObject wordList = ddddOcr.getWordByDet(bigBytes, 0.15);
			JSONObject centerJson = (wordList != null) ? wordList.getJSONObject("center") : null;
			int centerLen = (centerJson != null) ? centerJson.size() : -1;
			if (centerLen < 3) {
				System.err.println(centerJson + " -> size less 3");
				retEntity.setMsg("size[" + centerLen + "] not 3");
				return retEntity;
			}
			String word, centerXy;
			List<String> centerPoints = new ArrayList<>();
			for (int i = 0; i < 3; i++) {
				word = title.substring(i, i + 1);
				centerXy = centerJson.getString(word);
				if (centerXy == null) {
					continue;
				}
				centerPoints.add(centerXy);
			}
			// 将中心点用"|"连接
			String result = String.join("|", centerPoints);
			long cost = System.currentTimeMillis() - begin;
			if (centerPoints.size() != 3) {
				System.err.println(result + " -> size not 3");
				retEntity.setMsg("size[" + centerPoints.size() + "] not 3");
				return retEntity;
			}
			System.out.println("      |title=" + title + ",result=" + result + "->cost=" + cost);

			/// word click
			WebElement bgElement = driver.findElement(By.id("captchaImage2_mobile"));
			boolean isRobot = false;
			if (isRobot) {
				RobotMove.wordClickExec(bgElement, 73, 1.0, result);
			} else
				ActionMove.wordClickExec(driver, bgElement, 1.0, result);
			Thread.sleep(500);

			WebElement succElement = ChromeUtil.waitElement(driver, By.xpath("//p[@id='captchaImage_mobile_success' and not(contains(@style,'display: none'))]"), 30);
			String succTxt = (succElement != null) ? succElement.getText() : null;
			System.out.println("      |succTxt=" + succTxt);

			// 4 获取短信验证码
			WebElement sendElement = ChromeUtil.waitElement(driver, By.xpath("//span[@id='idenCodePhone']"), 1);
			((JavascriptExecutor) driver).executeScript("arguments[0].click();", sendElement);

			WebElement gtElement = ChromeUtil.waitElement(driver, By.xpath("//span[@id='idenCodePhoneNum' and contains(.,'秒后重新获取')]"), 30);
			String msg = (gtElement != null) ? gtElement.getText() : null;
			retEntity.setMsg("msg:" + msg);
			if (msg != null) {
				retEntity.setRet(0);
				JSONObject bboxJson = wordList.getJSONObject("bbox");
				String ck = GenChecksumUtil.genChecksum(bigBytes);
				String out = dataPath + "data" + File.separator + title + "_" + ck;
				ResultWrite.writeFile(out, bigBytes, bboxJson.toJSONString(), true);
			}
			return retEntity;
		} catch (Exception e) {
			System.out.println("phone=" + phone + ",e=" + e.toString());
			for (StackTraceElement ele : e.getStackTrace()) {
				System.out.println(ele.toString());
			}
			return null;
		} finally {
			driver.manage().deleteAllCookies();
		}
	}

	public static void main(String[] args) throws Exception {
		PropertiesUtil.loadConf("eva");
		SendDriverApi msg = new JiuXian();
		SendTestUtil.testCase(args, msg, "62", 1000);
	}
}
