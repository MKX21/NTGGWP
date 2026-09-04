-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: course_platform_db
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=121 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',3,'add_permission'),(6,'Can change permission',3,'change_permission'),(7,'Can delete permission',3,'delete_permission'),(8,'Can view permission',3,'view_permission'),(9,'Can add group',2,'add_group'),(10,'Can change group',2,'change_group'),(11,'Can delete group',2,'delete_group'),(12,'Can view group',2,'view_group'),(13,'Can add user',4,'add_user'),(14,'Can change user',4,'change_user'),(15,'Can delete user',4,'delete_user'),(16,'Can view user',4,'view_user'),(17,'Can add content type',5,'add_contenttype'),(18,'Can change content type',5,'change_contenttype'),(19,'Can delete content type',5,'delete_contenttype'),(20,'Can view content type',5,'view_contenttype'),(21,'Can add session',6,'add_session'),(22,'Can change session',6,'change_session'),(23,'Can delete session',6,'delete_session'),(24,'Can view session',6,'view_session'),(25,'Can add 課程',11,'add_course'),(26,'Can change 課程',11,'change_course'),(27,'Can delete 課程',11,'delete_course'),(28,'Can view 課程',11,'view_course'),(29,'Can add 使用者資料',25,'add_profile'),(30,'Can change 使用者資料',25,'change_profile'),(31,'Can delete 使用者資料',25,'delete_profile'),(32,'Can view 使用者資料',25,'view_profile'),(33,'Can add 購課紀錄',18,'add_enrollment'),(34,'Can change 購課紀錄',18,'change_enrollment'),(35,'Can delete 購課紀錄',18,'delete_enrollment'),(36,'Can view 購課紀錄',18,'view_enrollment'),(37,'Can add 學習紀錄',20,'add_learningrecord'),(38,'Can change 學習紀錄',20,'change_learningrecord'),(39,'Can delete 學習紀錄',20,'delete_learningrecord'),(40,'Can view 學習紀錄',20,'view_learningrecord'),(41,'Can add 優惠券',9,'add_coupon'),(42,'Can change 優惠券',9,'change_coupon'),(43,'Can delete 優惠券',9,'delete_coupon'),(44,'Can view 優惠券',9,'view_coupon'),(45,'Can add 訂單',22,'add_order'),(46,'Can change 訂單',22,'change_order'),(47,'Can delete 訂單',22,'delete_order'),(48,'Can view 訂單',22,'view_order'),(49,'Can add 優惠券使用紀錄',10,'add_couponusage'),(50,'Can change 優惠券使用紀錄',10,'change_couponusage'),(51,'Can delete 優惠券使用紀錄',10,'delete_couponusage'),(52,'Can view 優惠券使用紀錄',10,'view_couponusage'),(53,'Can add 課程分類',14,'add_coursecategory'),(54,'Can change 課程分類',14,'change_coursecategory'),(55,'Can delete 課程分類',14,'delete_coursecategory'),(56,'Can view 課程分類',14,'view_coursecategory'),(57,'Can add 購物車',7,'add_cart'),(58,'Can change 購物車',7,'change_cart'),(59,'Can delete 購物車',7,'delete_cart'),(60,'Can view 購物車',7,'view_cart'),(61,'Can add 課程審核',13,'add_courseaudit'),(62,'Can change 課程審核',13,'change_courseaudit'),(63,'Can delete 課程審核',13,'delete_courseaudit'),(64,'Can view 課程審核',13,'view_courseaudit'),(65,'Can add 課程章節',15,'add_coursechapter'),(66,'Can change 課程章節',15,'change_coursechapter'),(67,'Can delete 課程章節',15,'delete_coursechapter'),(68,'Can view 課程章節',15,'view_coursechapter'),(69,'Can add 課程單元',16,'add_courselesson'),(70,'Can change 課程單元',16,'change_courselesson'),(71,'Can delete 課程單元',16,'delete_courselesson'),(72,'Can view 課程單元',16,'view_courselesson'),(73,'Can add 課程問答',17,'add_coursequestion'),(74,'Can change 課程問答',17,'change_coursequestion'),(75,'Can delete 課程問答',17,'delete_coursequestion'),(76,'Can view 課程問答',17,'view_coursequestion'),(77,'Can add 課程回答',12,'add_courseanswer'),(78,'Can change 課程回答',12,'change_courseanswer'),(79,'Can delete 課程回答',12,'delete_courseanswer'),(80,'Can view 課程回答',12,'view_courseanswer'),(81,'Can add 通知',21,'add_notification'),(82,'Can change 通知',21,'change_notification'),(83,'Can delete 通知',21,'delete_notification'),(84,'Can view 通知',21,'view_notification'),(85,'Can add 訂單明細',23,'add_orderitem'),(86,'Can change 訂單明細',23,'change_orderitem'),(87,'Can delete 訂單明細',23,'delete_orderitem'),(88,'Can view 訂單明細',23,'view_orderitem'),(89,'Can add 付款紀錄',24,'add_payment'),(90,'Can change 付款紀錄',24,'change_payment'),(91,'Can delete 付款紀錄',24,'delete_payment'),(92,'Can view 付款紀錄',24,'view_payment'),(93,'Can add 促銷活動',26,'add_promotion'),(94,'Can change 促銷活動',26,'change_promotion'),(95,'Can delete 促銷活動',26,'delete_promotion'),(96,'Can view 促銷活動',26,'view_promotion'),(97,'Can add 退款紀錄',27,'add_refund'),(98,'Can change 退款紀錄',27,'change_refund'),(99,'Can delete 退款紀錄',27,'delete_refund'),(100,'Can view 退款紀錄',27,'view_refund'),(101,'Can add 使用者優惠券',29,'add_usercoupon'),(102,'Can change 使用者優惠券',29,'change_usercoupon'),(103,'Can delete 使用者優惠券',29,'delete_usercoupon'),(104,'Can view 使用者優惠券',29,'view_usercoupon'),(105,'Can add 購物車明細',8,'add_cartitem'),(106,'Can change 購物車明細',8,'change_cartitem'),(107,'Can delete 購物車明細',8,'delete_cartitem'),(108,'Can view 購物車明細',8,'view_cartitem'),(109,'Can add 收藏課程',19,'add_favorite'),(110,'Can change 收藏課程',19,'change_favorite'),(111,'Can delete 收藏課程',19,'delete_favorite'),(112,'Can view 收藏課程',19,'view_favorite'),(113,'Can add 課程評價',28,'add_review'),(114,'Can change 課程評價',28,'change_review'),(115,'Can delete 課程評價',28,'delete_review'),(116,'Can view 課程評價',28,'view_review'),(117,'Can add 單元觀看進度',30,'add_lessonprogress'),(118,'Can change 單元觀看進度',30,'change_lessonprogress'),(119,'Can delete 單元觀看進度',30,'delete_lessonprogress'),(120,'Can view 單元觀看進度',30,'view_lessonprogress');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user`
--

DROP TABLE IF EXISTS `auth_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `password` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `first_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(254) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user`
--

LOCK TABLES `auth_user` WRITE;
/*!40000 ALTER TABLE `auth_user` DISABLE KEYS */;
INSERT INTO `auth_user` VALUES (1,'pbkdf2_sha256$1200000$KCU4VhduBzaUls0kwd658Y$RKavBqNbN2dBDHjvIx7iDUR9bD5VmLWFYS14fqn12vE=',NULL,1,'admin_demo','','','admin@example.com',1,1,'2026-07-19 16:04:42.812980'),(2,'pbkdf2_sha256$1200000$5tYE26XzAtjR84jGsUtj9f$kFa1o+KkqY58XKpKiNzQzKKyddtlDWA+UrCCHPdRcEA=','2026-07-21 15:56:08.138345',0,'teacher_python','','','teacher_python@example.com',0,1,'2026-07-19 16:04:42.816741'),(3,'pbkdf2_sha256$1200000$edrSt0zA9NGHqrsah36jMd$dkD6ad//JTsTnl8XfBUA0k3xwe+CnsnrJPUueyeQycc=','2026-07-19 16:47:36.070480',0,'teacher_design','','','teacher_design@example.com',0,1,'2026-07-19 16:04:42.819666'),(4,'pbkdf2_sha256$1200000$4MXOyOBL1ESJgcHasRsch2$cyb3b1BuGnpVIMvCZ/0C3AsYNwmvlmng3k1c2dRUqZM=','2026-07-21 15:56:46.976070',0,'student_amy','','','amy@example.com',0,1,'2026-07-19 16:04:42.822318'),(5,'pbkdf2_sha256$1200000$luZx6Breexoqy6eK6zw6tC$6yzRDR5Xcj1al+QVYl7+m3cPZ2LO9NFRzw8rSYjKW04=','2026-07-20 14:58:04.393308',0,'student_ben','','','ben@example.com',0,1,'2026-07-19 16:04:42.825130'),(6,'pbkdf2_sha256$1200000$jFjmFYSBHSaktql4V75BCZ$6+SrBihpKo8kdF0H4bIVWNSkW0rbhPROPRiUKLHNqnA=','2026-07-20 14:58:35.048927',0,'student_cindy','','','cindy@example.com',0,1,'2026-07-19 16:04:42.827684'),(7,'pbkdf2_sha256$1200000$NAjKnKUrLg8MEPQpllii2T$d1RrIwtlfvnPBpMr68w2aA5yrdEHKHLu2LbcsewIn4A=','2026-07-21 16:06:03.969424',1,'admin','','','admin@local',1,1,'2026-07-19 16:12:05.187334'),(8,'pbkdf2_sha256$1200000$K7HLVl92f5n0RxlsdzDiCp$K5vVU+JOe4/tfVWZO0p7/tMp/qpXLXkRE1tEgNb8Onw=','2026-07-21 15:51:01.112443',0,'justin','','','test123@gmail.com',0,1,'2026-07-20 09:01:17.312990'),(9,'pbkdf2_sha256$1200000$5NSOpxphgR4Mr6sJ4WC1R3$fWIru+K9AO8evA6ls8x4jOMfGyhf9nVcgJ1v6MNKsIw=','2026-07-20 15:44:43.173898',0,'max','','','max@gmail.com',0,1,'2026-07-20 15:40:46.520555');
/*!40000 ALTER TABLE `auth_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_groups`
--

DROP TABLE IF EXISTS `auth_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_groups`
--

LOCK TABLES `auth_user_groups` WRITE;
/*!40000 ALTER TABLE `auth_user_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_user_permissions`
--

DROP TABLE IF EXISTS `auth_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_user_permissions`
--

LOCK TABLES `auth_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `auth_user_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext COLLATE utf8mb4_unicode_ci,
  `object_repr` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
INSERT INTO `django_admin_log` VALUES (1,'2026-07-19 16:51:25.532530','6','67大賽 - 審核通過',2,'[{\"changed\": {\"fields\": [\"\\u5be9\\u6838\\u72c0\\u614b\", \"\\u5be9\\u6838\\u610f\\u898b\", \"\\u5be9\\u6838\\u6642\\u9593\"]}}]',13,7),(2,'2026-07-19 16:52:31.747523','6','67大賽 - 審核通過',2,'[]',13,7),(3,'2026-07-19 16:55:23.417362','6','67大賽 - 審核通過',2,'[]',13,7),(4,'2026-07-19 16:58:17.788813','6','67大賽',2,'[{\"changed\": {\"fields\": [\"\\u662f\\u5426\\u4e0a\\u67b6\"]}}]',11,7),(5,'2026-07-19 17:07:33.954730','10','課程分類改進 - 審核通過',2,'[{\"changed\": {\"fields\": [\"\\u5be9\\u6838\\u4eba\\u54e1\", \"\\u5be9\\u6838\\u72c0\\u614b\", \"\\u5be9\\u6838\\u6642\\u9593\"]}}]',13,7),(6,'2026-07-19 17:07:46.426897','10','課程分類改進',2,'[{\"changed\": {\"fields\": [\"\\u662f\\u5426\\u4e0a\\u67b6\"]}}]',11,7),(7,'2026-07-19 17:17:10.588179','7','語言學習',1,'[{\"added\": {}}]',14,7),(8,'2026-07-19 17:17:32.769583','8','影視製作',1,'[{\"added\": {}}]',14,7),(9,'2026-07-20 08:17:38.213886','11','67 - 審核通過',2,'[{\"changed\": {\"fields\": [\"\\u5be9\\u6838\\u72c0\\u614b\", \"\\u5be9\\u6838\\u6642\\u9593\"]}}]',13,7),(10,'2026-07-20 08:17:51.058289','11','67',2,'[{\"changed\": {\"fields\": [\"\\u662f\\u5426\\u4e0a\\u67b6\"]}}]',11,7),(11,'2026-07-20 08:25:32.091238','11','67 - 審核通過',2,'[]',13,7),(12,'2026-07-20 09:33:31.138466','27','teacher_python - 課程已送審',2,'[]',21,7),(13,'2026-07-20 09:33:40.592309','12','test video - 審核通過',2,'[{\"changed\": {\"fields\": [\"\\u5be9\\u6838\\u72c0\\u614b\", \"\\u5be9\\u6838\\u6642\\u9593\"]}}]',13,7),(14,'2026-07-20 09:33:59.561636','12','test video',2,'[{\"changed\": {\"fields\": [\"\\u662f\\u5426\\u4e0a\\u67b6\"]}}]',11,7),(15,'2026-07-20 09:38:54.269772','3','test123 - test',1,'[{\"added\": {}}]',9,7),(16,'2026-07-20 15:35:59.320677','13','奶蛙吐舌頭 - 審核通過',2,'[{\"changed\": {\"fields\": [\"\\u5be9\\u6838\\u72c0\\u614b\"]}}]',13,7),(17,'2026-07-20 15:36:33.682738','13','奶蛙吐舌頭',2,'[{\"changed\": {\"fields\": [\"\\u662f\\u5426\\u4e0a\\u67b6\"]}}]',11,7),(18,'2026-07-20 16:13:46.993902','14','teach - 審核通過',2,'[{\"changed\": {\"fields\": [\"\\u5be9\\u6838\\u72c0\\u614b\"]}}]',13,7),(19,'2026-07-20 16:14:01.254231','14','teach',2,'[{\"changed\": {\"fields\": [\"\\u662f\\u5426\\u4e0a\\u67b6\"]}}]',11,7);
/*!40000 ALTER TABLE `django_admin_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (1,'admin','logentry'),(2,'auth','group'),(3,'auth','permission'),(4,'auth','user'),(5,'contenttypes','contenttype'),(7,'main','cart'),(8,'main','cartitem'),(9,'main','coupon'),(10,'main','couponusage'),(11,'main','course'),(12,'main','courseanswer'),(13,'main','courseaudit'),(14,'main','coursecategory'),(15,'main','coursechapter'),(16,'main','courselesson'),(17,'main','coursequestion'),(18,'main','enrollment'),(19,'main','favorite'),(20,'main','learningrecord'),(30,'main','lessonprogress'),(21,'main','notification'),(22,'main','order'),(23,'main','orderitem'),(24,'main','payment'),(25,'main','profile'),(26,'main','promotion'),(27,'main','refund'),(28,'main','review'),(29,'main','usercoupon'),(6,'sessions','session');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2026-07-19 16:03:45.008573'),(2,'auth','0001_initial','2026-07-19 16:03:45.418057'),(3,'admin','0001_initial','2026-07-19 16:03:45.520775'),(4,'admin','0002_logentry_remove_auto_add','2026-07-19 16:03:45.526280'),(5,'admin','0003_logentry_add_action_flag_choices','2026-07-19 16:03:45.531993'),(6,'contenttypes','0002_remove_content_type_name','2026-07-19 16:03:45.618913'),(7,'auth','0002_alter_permission_name_max_length','2026-07-19 16:03:45.661554'),(8,'auth','0003_alter_user_email_max_length','2026-07-19 16:03:45.680392'),(9,'auth','0004_alter_user_username_opts','2026-07-19 16:03:45.685711'),(10,'auth','0005_alter_user_last_login_null','2026-07-19 16:03:45.730494'),(11,'auth','0006_require_contenttypes_0002','2026-07-19 16:03:45.733804'),(12,'auth','0007_alter_validators_add_error_messages','2026-07-19 16:03:45.741063'),(13,'auth','0008_alter_user_username_max_length','2026-07-19 16:03:45.811098'),(14,'auth','0009_alter_user_last_name_max_length','2026-07-19 16:03:45.856185'),(15,'auth','0010_alter_group_name_max_length','2026-07-19 16:03:45.871185'),(16,'auth','0011_update_proxy_permissions','2026-07-19 16:03:45.877255'),(17,'auth','0012_alter_user_first_name_max_length','2026-07-19 16:03:45.925141'),(18,'main','0001_initial','2026-07-19 16:03:46.188597'),(19,'main','0002_learningrecord','2026-07-19 16:03:46.312307'),(20,'main','0003_coupon_order_couponusage','2026-07-19 16:03:46.690124'),(21,'main','0004_coursecategory_course_is_published_course_level_and_more','2026-07-19 16:03:48.562030'),(22,'sessions','0001_initial','2026-07-19 16:03:48.588432'),(23,'main','0005_courselesson_video_file','2026-07-20 08:54:18.531491'),(24,'main','0006_payment_expire_at_payment_payment_code_and_more','2026-07-20 14:52:57.329206'),(25,'main','0007_lessonprogress','2026-07-21 09:36:20.917468'),(26,'main','0008_profile_avatar','2026-07-21 15:47:13.281675');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `session_data` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
INSERT INTO `django_session` VALUES ('0kjigz52uwbugrstcb5hdm7eguii6z8q','.eJxVjEEOwiAQAP-yZ0O2QCn06N03kAUWqRpISnsy_t006UGvM5N5g6d9K37vvPolwQwSLr8sUHxyPUR6UL03EVvd1iWIIxGn7eLWEr-uZ_s3KNQLzJCRM2pCqy1b6eJgLEdntFWKSatJuUgGY2LOdhzQJXRJhsmQITKjQvh8Ad3pN6w:1wljnn:KhVm-HD9Xjkyhh_DiB6qt9f5Q1SXijfisjDGFpRwUvM','2026-08-03 08:56:43.367746'),('1s4fbnjz9su4uixanydkf7s7e0k5v71k','.eJxVjEEOwiAQAP-yZ0O2QCn06N03kAUWqRpISnsy_t006UGvM5N5g6d9K37vvPolwQwSLr8sUHxyPUR6UL03EVvd1iWIIxGn7eLWEr-uZ_s3KNQLzJCRM2pCqy1b6eJgLEdntFWKSatJuUgGY2LOdhzQJXRJhsmQITKjQvh8Ad3pN6w:1wlUfr:KoDUMkqUPKWHMsFCD0Rt4E-9jFHs-5GZB9dMeXd-x4M','2026-08-02 16:47:31.937953'),('1ufcwacrb438id92qzcztmgvqwbprqd9','.eJxVjLsOwjAMAP_FM4pkJ3EfIzvfULmxSwsokZp2Qvw7qtQB1rvTvWGQfZuHvdo6LAo9NHD5ZaOkp-VD6EPyvbhU8rYuozsSd9rqbkXtdT3bv8EsdYYeOLFMFAUxKIuxjzz5KaJhsg7NWBqirm0iiRIFz4jBh0gtoVJghM8X2q82qQ:1wmCpC:tGFZe6cWkqCnGiIcuB792xOp0-0oF429Qt1-8SJjdKI','2026-08-04 15:56:06.604331'),('58z901fr7u99ko7d0p8s7ld496azgtfw','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wmBUy:av1zYkGv2Q9nzQIuDbiasFTfIdKz9vPyEETzk-l3iDg','2026-08-04 14:31:08.609142'),('5pah3quqhafqw6crn5ce8g9tl5bl848i','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wmBmX:8-N8YadHW3wXwYUTPTKhz0pp1qTaurnWTLi2-HbP2C0','2026-08-04 14:49:17.485390'),('6utqrpiyv4q457czpvc4cub6ncxowbmi','.eJxVjLsOwjAMAP_FM4pkJ3EfIzvfULmxSwsokZp2Qvw7qtQB1rvTvWGQfZuHvdo6LAo9NHD5ZaOkp-VD6EPyvbhU8rYuozsSd9rqbkXtdT3bv8EsdYYeOLFMFAUxKIuxjzz5KaJhsg7NWBqirm0iiRIFz4jBh0gtoVJghM8X2q82qQ:1wlk0S:MzP4WZaZjtdD2RDDgfUGoxHGPeXulljt8WAtihYI5w8','2026-08-03 09:09:48.247880'),('7btxqftd72rgdundaca4zm1vtpm5qc17','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wm6yo:_w62EuukbB_lNKF6wpBy217IChQ8rVp7hR2zKp_YE3E','2026-08-04 09:41:38.745887'),('7gf3nuv8mke6vb0jqulrr4fga3yj7wh0','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wlUHs:o8pvmKnX2yepqlt4rJJt4RrUkFckib52SU_aOIzccvc','2026-08-02 16:22:44.070205'),('7t9ohp5s9dd1tlzb8i4h8s11r2xh9ymk','.eJxVjEEOwiAQAP-yZ0O2QCn06N03kAUWqRpISnsy_t006UGvM5N5g6d9K37vvPolwQwSLr8sUHxyPUR6UL03EVvd1iWIIxGn7eLWEr-uZ_s3KNQLzJCRM2pCqy1b6eJgLEdntFWKSatJuUgGY2LOdhzQJXRJhsmQITKjQvh8Ad3pN6w:1wlp7J:wqqwulOqQ7dfyoqYoGyHUnmx7e8s2H6m32egC9GxIUw','2026-08-03 14:37:13.295507'),('7zynzkqttaj6dq03l3a6ib96iy9tcu9r','.eJxVjEEOwiAQAP-yZ0O2QCn06N03kAUWqRpISnsy_t006UGvM5N5g6d9K37vvPolwQwSLr8sUHxyPUR6UL03EVvd1iWIIxGn7eLWEr-uZ_s3KNQLzJCRM2pCqy1b6eJgLEdntFWKSatJuUgGY2LOdhzQJXRJhsmQITKjQvh8Ad3pN6w:1wlUtt:OZfk3_WJDOrkRUkd_5BN3fSohILIz4k9-LVnoKV9TB0','2026-08-02 17:02:01.255564'),('8yxq737ifsbkuxsv6dkxd8fw1lmeyzt3','.eJxVjLsOwjAMAP_FM4pkJ3EfIzvfULmxSwsokZp2Qvw7qtQB1rvTvWGQfZuHvdo6LAo9NHD5ZaOkp-VD6EPyvbhU8rYuozsSd9rqbkXtdT3bv8EsdYYeOLFMFAUxKIuxjzz5KaJhsg7NWBqirm0iiRIFz4jBh0gtoVJghM8X2q82qQ:1wlpFX:iigVsQJWzgK7IFgp9P885xBMVd-0xDERGy4wRPwkX90','2026-08-03 14:45:43.942020'),('95gy0whtkuot5gkq0nzdh1humxefok5c','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wlpA3:Z7HBNsu4c6lsxH9B3C3KVMahzU69YZXQfktZDlIftOg','2026-08-03 14:40:03.512015'),('9sjho0aa73kbpfql2ge2ew4dwx2qtjw0','.eJxVjDEOgzAMAP_iuYoSYpKGsTtvQI7tFNoKJAJT1b9XSAztene6Nwy0b-OwV12HSaADD5dflomfOh9CHjTfF8PLvK1TNkdiTltNv4i-bmf7NxipjtCBJm18cRR8cYkL-9Rmjt7aRDYhRhsLJqcSBa1w43IOIQRk9NriVQg-X-BgN6g:1wlUfv:TrIHKCI04iBxZLLVf0bFPctftVArAm0U81hx2ZOEcP4','2026-08-02 16:47:35.281910'),('9yiks0pm4g0dej3dnhu2w653mq6sb17e','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wljTU:Sv5rljTiGZLR0qZhYo8xWetfPhtA3Hb6azimw0F_ZTQ','2026-08-03 08:35:44.070772'),('aai3e72qxansqkccfgn5t0w098l2g8am','.eJxVjLsOgkAQAP9la3PxHt4Cpb3fQPb2IaiBhIPK-O-GhELbmcm8oadtHfqt6tKPAh1kOP2yQvzUaRfyoOk-O56ndRmL2xN32Opus-jrerR_g4HqAB1QMp8keTUfSqNNOLPYxcRKtqzRyAK3agmjEiNiiYxeQouRM2Yt8PkCG6g5OA:1wlozL:f5u2Ba4h0Uorho0mBNwtoX35QrgyVX2SoRvnBwFrLrI','2026-08-03 14:28:59.277974'),('acxjbq7jtdwt6lr13gc6r3g77kzqe663','.eJxVjLsOwjAMAP_FM4pkJ3EfIzvfULmxSwsokZp2Qvw7qtQB1rvTvWGQfZuHvdo6LAo9NHD5ZaOkp-VD6EPyvbhU8rYuozsSd9rqbkXtdT3bv8EsdYYeOLFMFAUxKIuxjzz5KaJhsg7NWBqirm0iiRIFz4jBh0gtoVJghM8X2q82qQ:1wmBV0:88QXPIwW8E9G9VFWdmF7QUd9ETA4CmdYc-IyH3T8Iyk','2026-08-04 14:31:10.136014'),('agua0tc2v11aiysvx190pwffjs6hydnn','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wlj7J:JSePBdqlTVejl2ddIRdIiU53dfMQRte46H1tPJWsmVU','2026-08-03 08:12:49.057135'),('aqtj28gltisj3lea1im1yv5hy1oba4sr','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wlkDv:_FPaqArWU4k3Vfu43v_ZK1YnYD5MYnjpQdedWmbhRiQ','2026-08-03 09:23:43.891811'),('asyzgyzdxe7j2zz23piq5zvbg30kp29v','.eJxVjLsOwjAMAP_FM4pkJ3EfIzvfULmxSwsokZp2Qvw7qtQB1rvTvWGQfZuHvdo6LAo9NHD5ZaOkp-VD6EPyvbhU8rYuozsSd9rqbkXtdT3bv8EsdYYeOLFMFAUxKIuxjzz5KaJhsg7NWBqirm0iiRIFz4jBh0gtoVJghM8X2q82qQ:1wlp7K:yRPklKswEPv7LW9DIye5dKdOYI5C6q59nil5FspbSy0','2026-08-03 14:37:14.065378'),('avxzcg1n0aed5u8su958cqznk5tiai60','.eJxVjLsOwjAMAP_FM4pkJ3EfIzvfULmxSwsokZp2Qvw7qtQB1rvTvWGQfZuHvdo6LAo9NHD5ZaOkp-VD6EPyvbhU8rYuozsSd9rqbkXtdT3bv8EsdYYeOLFMFAUxKIuxjzz5KaJhsg7NWBqirm0iiRIFz4jBh0gtoVJghM8X2q82qQ:1wlovy:nXIq2ZxpEJed-jI91FvYm6u8sWzN_R895erLWVAaqRc','2026-08-03 14:25:30.328988'),('b33ewxubclxid5941r59lcq1ofiyxc5g','.eJxVjLsOwjAMAP_FM4pkJ3EfIzvfULmxSwsokZp2Qvw7qtQB1rvTvWGQfZuHvdo6LAo9NHD5ZaOkp-VD6EPyvbhU8rYuozsSd9rqbkXtdT3bv8EsdYYeOLFMFAUxKIuxjzz5KaJhsg7NWBqirm0iiRIFz4jBh0gtoVJghM8X2q82qQ:1wlpJS:nj3d2MtU36IY-UsOTO0ndoRNgcFOVbDWwNnh_05T9m0','2026-08-03 14:49:46.741843'),('ccu3vgax2v25nkyx62bzw4uwlao6xeyk','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wm79j:_QrA-4bIK4bj-OqsazD4MqMjAJfw7NO-I-Dr2KArKhI','2026-08-04 09:52:55.161555'),('drwpubjlsabvxnw5s4rkldkp4gwm51ht','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wmBoA:rMw1I_-sbeb9cgwrbXTq9OQO7e-467kos55M_2HGLE8','2026-08-04 14:50:58.227909'),('f1mdurnmvrfvzmgdc6yrp6vtqlnc772c','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wlUHM:sMBcegVpHR6FlIhRhpDtq4KRcLDv94_NzC5RqDDHbLQ','2026-08-02 16:22:12.163100'),('fux6w2wlr5ci2siecj7zasaxbdi7wz7y','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wmCj5:ul3Tl2-47gz8_Z9HVVy5vpzLSYMdl3sRveWRCRMmTns','2026-08-04 15:49:47.483738'),('fwyve6zwafed1eyagrpqehxwh90l36q8','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wlpRR:x0DBpB-xIoti7BqTpDbMQjvcRj8eJUwoYsUcgc01Rso','2026-08-03 14:58:01.138082'),('hfljnu1oyadkuiyi0uhs3p2qnasjnpq9','.eJxVjLsOgkAQAP9la3PxHt4Cpb3fQPb2IaiBhIPK-O-GhELbmcm8oadtHfqt6tKPAh1kOP2yQvzUaRfyoOk-O56ndRmL2xN32Opus-jrerR_g4HqAB1QMp8keTUfSqNNOLPYxcRKtqzRyAK3agmjEiNiiYxeQouRM2Yt8PkCG6g5OA:1wlUft:et3op4XIon5h2MKtQBmiO9ytS_56d4YFFJaWapV2SC8','2026-08-02 16:47:33.667313'),('hlsres1xeosubc4gaiyftx7hntz6rlyl','.eJxVjLsOwjAMAP_FM4pkJ3EfIzvfULmxSwsokZp2Qvw7qtQB1rvTvWGQfZuHvdo6LAo9NHD5ZaOkp-VD6EPyvbhU8rYuozsSd9rqbkXtdT3bv8EsdYYeOLFMFAUxKIuxjzz5KaJhsg7NWBqirm0iiRIFz4jBh0gtoVJghM8X2q82qQ:1wlpEm:_Gjwz15BqA-unjKKyEjNzzIvTu_BG6c30wiJ56GyHYs','2026-08-03 14:44:56.573032'),('hrflm9c154welyrs1ll3csmcknonqjla','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wm6wM:qjKhnIGvb1i7XhV6TGbyYhdHl3JhYMi3AjqAGkiNDcE','2026-08-04 09:39:06.986988'),('hu3a12aq3z5z3tsyhec3ekcrlcnkjzh6','.eJxVjLsOwjAMAP_FM4pkJ3EfIzvfULmxSwsokZp2Qvw7qtQB1rvTvWGQfZuHvdo6LAo9NHD5ZaOkp-VD6EPyvbhU8rYuozsSd9rqbkXtdT3bv8EsdYYeOLFMFAUxKIuxjzz5KaJhsg7NWBqirm0iiRIFz4jBh0gtoVJghM8X2q82qQ:1wlpI3:ZnHM157DCfBBnNlcwF2tP9opBWRGs-d9AFzWDLuTkis','2026-08-03 14:48:19.944498'),('i3m2ltddferk96135o4rp9n1v553hs29','.eJxVjEEOwiAQAP-yZ0O2QCn06N03kAUWqRpISnsy_t006UGvM5N5g6d9K37vvPolwQwSLr8sUHxyPUR6UL03EVvd1iWIIxGn7eLWEr-uZ_s3KNQLzJCRM2pCqy1b6eJgLEdntFWKSatJuUgGY2LOdhzQJXRJhsmQITKjQvh8Ad3pN6w:1wlovx:nkHr_JORN-4F3daaUxGyTbAPIJkZTiBUlnMTx2LVC_Y','2026-08-03 14:25:29.571611'),('i8qgoxfgniv2rjev54x7byysaid13z7e','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wmCpq:fzq3BYaJMSBC1wv8jlxD9IXlPh_55uW6_t8kWaghcuc','2026-08-04 15:56:46.977934'),('iw8ny72sx81zna727fxyxjx96eytatpi','.eJxVjEEOwiAQAP-yZ0O2QCn06N03kAUWqRpISnsy_t006UGvM5N5g6d9K37vvPolwQwSLr8sUHxyPUR6UL03EVvd1iWIIxGn7eLWEr-uZ_s3KNQLzJCRM2pCqy1b6eJgLEdntFWKSatJuUgGY2LOdhzQJXRJhsmQITKjQvh8Ad3pN6w:1wljkr:eJgFIfDllKi91vAr622tle6QEkBpMwANm5dcMfB5wjg','2026-08-03 08:53:41.051345'),('jkbcbhpkhmujfnah90qsgwpgf2y4xz5q','.eJxVjEEOwiAQAP-yZ0O2QCn06N03kAUWqRpISnsy_t006UGvM5N5g6d9K37vvPolwQwSLr8sUHxyPUR6UL03EVvd1iWIIxGn7eLWEr-uZ_s3KNQLzJCRM2pCqy1b6eJgLEdntFWKSatJuUgGY2LOdhzQJXRJhsmQITKjQvh8Ad3pN6w:1wm6yq:603Wdk6uS2NWcQaPs917_oYPfoaTIPSL0v9mOsplTJ4','2026-08-04 09:41:40.610305'),('lgr69uk5vyo4w82wmtvfzypxc3o8vwyv','.eJxVjLsOwjAMAP_FM4pkJ3EfIzvfULmxSwsokZp2Qvw7qtQB1rvTvWGQfZuHvdo6LAo9NHD5ZaOkp-VD6EPyvbhU8rYuozsSd9rqbkXtdT3bv8EsdYYeOLFMFAUxKIuxjzz5KaJhsg7NWBqirm0iiRIFz4jBh0gtoVJghM8X2q82qQ:1wlUfs:8gkYpDaGx3drvsSitrVXNL1J9S6dUvH88ffOt_gT8uQ','2026-08-02 16:47:32.860228'),('lrix020aaxnvql5fzps7vn683xtyain5','.eJxVjEEOwiAQAP-yZ0O2QCn06N03kAUWqRpISnsy_t006UGvM5N5g6d9K37vvPolwQwSLr8sUHxyPUR6UL03EVvd1iWIIxGn7eLWEr-uZ_s3KNQLzJCRM2pCqy1b6eJgLEdntFWKSatJuUgGY2LOdhzQJXRJhsmQITKjQvh8Ad3pN6w:1wmBUz:puoT1kKBQlk9b75SZgJ0RGwQC7oIEBrk3N6MH8Su5hM','2026-08-04 14:31:09.369978'),('mhji1xmqrk39z8y6r4duk1re8tez87q4','.eJxVjEEOwiAQAP-yZ0O2QCn06N03kAUWqRpISnsy_t006UGvM5N5g6d9K37vvPolwQwSLr8sUHxyPUR6UL03EVvd1iWIIxGn7eLWEr-uZ_s3KNQLzJCRM2pCqy1b6eJgLEdntFWKSatJuUgGY2LOdhzQJXRJhsmQITKjQvh8Ad3pN6w:1wlk0R:tS-6lb2-MkGSDUX_76FpbOm2rqnpMEsI-Jd0aCNKXcA','2026-08-03 09:09:47.432154'),('mnrz9gs42if1vapvs5zlf3q4jlb1gq2m','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wlV3R:FxYloBv62AXqE1PCHyjlSz17xNy_mj9fUifruxQj-Lk','2026-08-02 17:11:53.584449'),('mzcdqosl7yxke6vvheat3hvjnpxb2tdz','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wljkq:h1E-9iMHmJMfyLQWqp9X480sjsMeIe_nb1hR7YKwAwM','2026-08-03 08:53:40.237932'),('n3ge5wiv0a2286kt2ot9ex0ssekqaqfp','.eJxVjEEOwiAQAP-yZ0O2QCn06N03kAUWqRpISnsy_t006UGvM5N5g6d9K37vvPolwQwSLr8sUHxyPUR6UL03EVvd1iWIIxGn7eLWEr-uZ_s3KNQLzJCRM2pCqy1b6eJgLEdntFWKSatJuUgGY2LOdhzQJXRJhsmQITKjQvh8Ad3pN6w:1wmCpE:Q9MTEjTNwrFz9rbf2OTvTiNddnjlQj7FsR7NrOc8lKk','2026-08-04 15:56:08.139862'),('n4b817xuupkeyptia252kiobxer9plfa','.eJxVjLsOgkAQAP9la3PxHt4Cpb3fQPb2IaiBhIPK-O-GhELbmcm8oadtHfqt6tKPAh1kOP2yQvzUaRfyoOk-O56ndRmL2xN32Opus-jrerR_g4HqAB1QMp8keTUfSqNNOLPYxcRKtqzRyAK3agmjEiNiiYxeQouRM2Yt8PkCG6g5OA:1wlp1p:9jDVZn3cJuRJ24YcGU7pX1IVTbJhsyRrdyGuS9Hm1pY','2026-08-03 14:31:33.376114'),('ow8055rf41woxiqzzhx9efnbalqislyj','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wljcB:4DPSmr1t0r5cvCq8gVzenggNDjlqOj8nQherICtb1c8','2026-08-03 08:44:43.019836'),('ppf0rd6llwucbgzz0oxa2g2eod2th1ov','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wlpRT:uUialbV11H5TY7AWQ-N9WgpkQ9iqzLO9mz_0_VPn0Hc','2026-08-03 14:58:03.606014'),('px3qx71kttfe96k26ftq23dlz5jhjkkg','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wmCis:uFAumTPNF5bBzLn9fagRHtbqSqoLaUTHfbWANz4sbEQ','2026-08-04 15:49:34.289865'),('pyjm4chz1lxfgbc6yzhlcmucfq2i7exm','.eJxVjDkOwjAQAP-yNbLW8cZHSvq8IbLXCw4gW8pRIf6OIqWAdmY0b5jivpVpX2WZ5gwD9HD5ZSnyU-oh8iPWe1Pc6rbMSR2JOu2qxpbldT3bv0GJa4EBAmUyyaaEkiQb8Ry4C9b1HSEHNNpZExnJRuq9sPU6O4OotUd_IyL4fAHc2jbg:1wlpRU:Bb36AJRHnbJYS8SW0k45u1W_Wo8KVpzVqUleJP5gI50','2026-08-03 14:58:04.395061'),('qk5k087pp3ggtn38y1t2zz7zyu8uu29m','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wmCpD:nHhposis-lDHqJWsFPg2K1EGCnhBg7NkpdP7sIzidzs','2026-08-04 15:56:07.369583'),('r8syztzffj1idkgr0cvn2e3487e2je5y','.eJxVjLsOgkAQAP9la3PxHt4Cpb3fQPb2IaiBhIPK-O-GhELbmcm8oadtHfqt6tKPAh1kOP2yQvzUaRfyoOk-O56ndRmL2xN32Opus-jrerR_g4HqAB1QMp8keTUfSqNNOLPYxcRKtqzRyAK3agmjEiNiiYxeQouRM2Yt8PkCG6g5OA:1wlpRz:Xr2NZCTccyPGPBHfMCq0Gj73S9GCkWlYCmPTt18C3kc','2026-08-03 14:58:35.050798'),('s94xsct1yczg1ywiga0pcoj396s7t0ar','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wlk3r:Qs92eRPThjtQY0Lc4TAPF5kgz-POuCBPPW5_C00YC1k','2026-08-03 09:13:19.495225'),('sbstei5yt5rthlvn699njqh4loc68qp0','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wmBVM:M22tgDXONyvZC-U6e-c9-f8vG_FnxLYaWd94Yt6fYnk','2026-08-04 14:31:32.682936'),('shk8cavozx0at65xlumu48cpmp74ai6l','.eJxVjDkOwjAQAP-yNbLW8cZHSvq8IbLXCw4gW8pRIf6OIqWAdmY0b5jivpVpX2WZ5gwD9HD5ZSnyU-oh8iPWe1Pc6rbMSR2JOu2qxpbldT3bv0GJa4EBAmUyyaaEkiQb8Ry4C9b1HSEHNNpZExnJRuq9sPU6O4OotUd_IyL4fAHc2jbg:1wlUfu:_dwt6qmrFXpGUDRpby0tmPrOoYMQNGNHCexv-jmw9fQ','2026-08-02 16:47:34.460334'),('sso5y2kir3viyg56r5ddno6jchf0ta7x','.eJxVjLsOwjAMAP_FM4pkJ3EfIzvfULmxSwsokZp2Qvw7qtQB1rvTvWGQfZuHvdo6LAo9NHD5ZaOkp-VD6EPyvbhU8rYuozsSd9rqbkXtdT3bv8EsdYYeOLFMFAUxKIuxjzz5KaJhsg7NWBqirm0iiRIFz4jBh0gtoVJghM8X2q82qQ:1wmCyp:NGA5XtJ6nLEyygPOU_bobT0YrPoEua5Btvw-anm0hBM','2026-08-04 16:06:03.971513'),('tm8fih0mzl5uz6pgpd1eum1xvpfotot7','.eJxVjDkOwjAQAP-yNbLW8cZHSvq8IbLXCw4gW8pRIf6OIqWAdmY0b5jivpVpX2WZ5gwD9HD5ZSnyU-oh8iPWe1Pc6rbMSR2JOu2qxpbldT3bv0GJa4EBAmUyyaaEkiQb8Ry4C9b1HSEHNNpZExnJRuq9sPU6O4OotUd_IyL4fAHc2jbg:1wljnp:mzLVhpEnRl8er3DlebskXWzZzeEeT9VTqTUPu33Hhb0','2026-08-03 08:56:45.131438'),('u2dchu3vudf4pakwodfug6siupl68kil','.eJxVjDEOgzAMAP_iuYoSYpKGsTtvQI7tFNoKJAJT1b9XSAztene6Nwy0b-OwV12HSaADD5dflomfOh9CHjTfF8PLvK1TNkdiTltNv4i-bmf7NxipjtCBJm18cRR8cYkL-9Rmjt7aRDYhRhsLJqcSBa1w43IOIQRk9NriVQg-X-BgN6g:1wlUfw:efhqaMDkWlFYgcO4Br7VlqvVfyBCOUjiUrvwPXE_GQY','2026-08-02 16:47:36.072284'),('u4tq2dl2zlio0o1ulqw4o8fybsnlsixt','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wmBmm:dNJPaqK0-DPizVF3xlqpi7y38p6k3YS7s5jWgsvcDAg','2026-08-04 14:49:32.924216'),('u8i6vr9e36m9gir4eu0qhqda6t6afb87','.eJxVjLsOgkAQAP9la3PxHt4Cpb3fQPb2IaiBhIPK-O-GhELbmcm8oadtHfqt6tKPAh1kOP2yQvzUaRfyoOk-O56ndRmL2xN32Opus-jrerR_g4HqAB1QMp8keTUfSqNNOLPYxcRKtqzRyAK3agmjEiNiiYxeQouRM2Yt8PkCG6g5OA:1wlpRS:kxsu9qCog6dWbxwRC4dHy-NNEaeMEx59eigAQWM4EX4','2026-08-03 14:58:02.795147'),('ubs026umovz6zn4okdmte5x977zju2rv','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wljno:93zS6lOTIYdttMZWwRWTgaWYv64_AixSKsAmLZ9SvqQ','2026-08-03 08:56:44.232370'),('v80e0r0mcdt8xoyl0ld5fpssihs7012c','.eJxVjEEOwiAQAP-yZ0O2QCn06N03kAUWqRpISnsy_t006UGvM5N5g6d9K37vvPolwQwSLr8sUHxyPUR6UL03EVvd1iWIIxGn7eLWEr-uZ_s3KNQLzJCRM2pCqy1b6eJgLEdntFWKSatJuUgGY2LOdhzQJXRJhsmQITKjQvh8Ad3pN6w:1wlUwM:QYWPpfeX5nXDNfgxWuylcbjLniZi3DbDfbje765lkRY','2026-08-02 17:04:34.120691'),('v997e2pk03j6ml2votorb1vv35iv2h3v','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wm78B:HsvhSTkDex6GR5H5X81aMCzi-YjcC6gfuSZHHshh0CI','2026-08-04 09:51:19.074363'),('vluewre91plc56dnwfiw6ekpktej97kw','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wmBnq:3dToSk21lMozWyMiGzqc2wqUpaHtY2wTcWkShcw3NO0','2026-08-04 14:50:38.639397'),('w4d4d7lkdaz2q5zwez59mczwc6r7yc12','.eJxVjLsOgkAQAP9la3PxHt4Cpb3fQPb2IaiBhIPK-O-GhELbmcm8oadtHfqt6tKPAh1kOP2yQvzUaRfyoOk-O56ndRmL2xN32Opus-jrerR_g4HqAB1QMp8keTUfSqNNOLPYxcRKtqzRyAK3agmjEiNiiYxeQouRM2Yt8PkCG6g5OA:1wlV3k:BqU8bixgWv5h793Sp89PIMNOkZ9gaAWVI9z8bR_nTZY','2026-08-02 17:12:12.710827'),('wwwlhaxn3p8drmms7azzsru40asfl7ju','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wlp7I:gVaJRSbQrX32qYRou7KAcbFSV5OAkWC95AX93uB41pw','2026-08-03 14:37:12.354029'),('wx42glrf8r7xjolz1bn87ki6h0spbbai','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wlj7s:g364Nyt-zNy0UqfeGaG9jCzDCFZNVeo-T7X1LQvFIpk','2026-08-03 08:13:24.843317'),('wzgruznz9n5shzpn1gvx56k2mw2vnjw9','.eJxVjLsOwjAMAP_FM4pkJ3EfIzvfULmxSwsokZp2Qvw7qtQB1rvTvWGQfZuHvdo6LAo9NHD5ZaOkp-VD6EPyvbhU8rYuozsSd9rqbkXtdT3bv8EsdYYeOLFMFAUxKIuxjzz5KaJhsg7NWBqirm0iiRIFz4jBh0gtoVJghM8X2q82qQ:1wm6yp:N56dn5k8aeSyrqzPSyfscr8_j_PFaqL57mV7ECzJFFU','2026-08-04 09:41:39.640703'),('x6uq7wah30db6qblt3nsr1ejuz07ai6q','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wlk4J:DabqAYxYnC1dpkVe0etYK1fLYzvULPnAiJPNxVmSwro','2026-08-03 09:13:47.720345'),('xf0wfwxemxp7o6jd4x2omf484dwzj3i1','.eJxVjDkOwjAQAP-yNbLW8cZHSvq8IbLXCw4gW8pRIf6OIqWAdmY0b5jivpVpX2WZ5gwD9HD5ZSnyU-oh8iPWe1Pc6rbMSR2JOu2qxpbldT3bv0GJa4EBAmUyyaaEkiQb8Ry4C9b1HSEHNNpZExnJRuq9sPU6O4OotUd_IyL4fAHc2jbg:1wlpRS:vBHQ04gMQvJ-GjKvH1LbQEhewY8HF0pVpYeBmYtso6o','2026-08-03 14:58:02.013406'),('xk1txfldwtzcrhhfjvja574v93earh5m','.eJxVjEEOwiAQAP-yZ0O2QCn06N03kAUWqRpISnsy_t006UGvM5N5g6d9K37vvPolwQwSLr8sUHxyPUR6UL03EVvd1iWIIxGn7eLWEr-uZ_s3KNQLzJCRM2pCqy1b6eJgLEdntFWKSatJuUgGY2LOdhzQJXRJhsmQITKjQvh8Ad3pN6w:1wm6sR:kgEIvfSwSm9cq0g62EzmQG1Mx59wZ6wFA-SqHQI0ttQ','2026-08-04 09:35:03.712608'),('xstd8y90ygn64uadbzh4lt7pb5td50jp','.eJxVjLsOwjAMAP_FM4pkJ3EfIzvfULmxSwsokZp2Qvw7qtQB1rvTvWGQfZuHvdo6LAo9NHD5ZaOkp-VD6EPyvbhU8rYuozsSd9rqbkXtdT3bv8EsdYYeOLFMFAUxKIuxjzz5KaJhsg7NWBqirm0iiRIFz4jBh0gtoVJghM8X2q82qQ:1wljkr:gnuqRX-d38bkYTLjFkHGsJOspFcx1HjYYjfNuRhiF_w','2026-08-03 08:53:41.860684'),('y31uwq58g0t76o6g4uadz2qr03db7dy6','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wmCjR:iFr5Q_Bm8JdkvbMNdMlWd1hNPcugAAKE_5bykAkyMMo','2026-08-04 15:50:09.199334'),('ydzbas0u1j4x3rjzlxhzkh5igzjn2i30','.eJxVjDEOwjAMAP_iGUUkKY3TkZ03VE5skwJqpKadEH9HlTrAene6N4y0rWXcmizjxDBAB6dflig_Zd4FP2i-V5PrvC5TMntiDtvMrbK8rkf7NyjUCgxA5LUTe845Zu0DRmZJntQli6IRfXQkYlEVg9jeq6PkHOnFMmLwDJ8vG1w5Bw:1wlp7i:6rTgU9-3Jy1DWNFT05eNYYIMmOhXZK5y7nkipxP3b0s','2026-08-03 14:37:38.010539');
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_cart`
--

DROP TABLE IF EXISTS `main_cart`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_cart` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `main_cart_user_id_53cf8b47_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_cart`
--

LOCK TABLES `main_cart` WRITE;
/*!40000 ALTER TABLE `main_cart` DISABLE KEYS */;
INSERT INTO `main_cart` VALUES (1,'2026-07-19 16:04:56.032596','2026-07-19 16:04:56.032607',4),(2,'2026-07-19 16:04:56.037365','2026-07-19 16:04:56.037376',5),(3,'2026-07-20 14:28:59.395597','2026-07-20 14:28:59.395614',6),(4,'2026-07-20 15:00:17.332419','2026-07-20 15:00:17.332434',8),(5,'2026-07-20 15:48:37.784134','2026-07-20 15:48:37.784151',2),(6,'2026-07-21 09:57:01.608379','2026-07-21 09:57:01.608396',7);
/*!40000 ALTER TABLE `main_cart` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_cartitem`
--

DROP TABLE IF EXISTS `main_cartitem`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_cartitem` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `added_at` datetime(6) NOT NULL,
  `cart_id` bigint NOT NULL,
  `course_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `main_cartitem_cart_id_course_id_575069f9_uniq` (`cart_id`,`course_id`),
  KEY `main_cartitem_course_id_6ec9eda5_fk_main_course_id` (`course_id`),
  CONSTRAINT `main_cartitem_cart_id_8357cf81_fk_main_cart_id` FOREIGN KEY (`cart_id`) REFERENCES `main_cart` (`id`),
  CONSTRAINT `main_cartitem_course_id_6ec9eda5_fk_main_course_id` FOREIGN KEY (`course_id`) REFERENCES `main_course` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_cartitem`
--

LOCK TABLES `main_cartitem` WRITE;
/*!40000 ALTER TABLE `main_cartitem` DISABLE KEYS */;
INSERT INTO `main_cartitem` VALUES (12,'2026-07-21 15:51:49.922498',4,13);
/*!40000 ALTER TABLE `main_cartitem` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_coupon`
--

DROP TABLE IF EXISTS `main_coupon`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_coupon` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `discount_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `discount_value` int unsigned NOT NULL,
  `min_spend` int unsigned NOT NULL,
  `start_date` datetime(6) NOT NULL,
  `end_date` datetime(6) NOT NULL,
  `usage_limit` int unsigned NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`),
  CONSTRAINT `main_coupon_chk_1` CHECK ((`discount_value` >= 0)),
  CONSTRAINT `main_coupon_chk_2` CHECK ((`min_spend` >= 0)),
  CONSTRAINT `main_coupon_chk_3` CHECK ((`usage_limit` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_coupon`
--

LOCK TABLES `main_coupon` WRITE;
/*!40000 ALTER TABLE `main_coupon` DISABLE KEYS */;
INSERT INTO `main_coupon` VALUES (1,'NEW100','新會員折扣','amount',100,500,'2026-07-18 16:04:56.011797','2026-09-17 16:04:56.011797',0,1,'2026-07-19 16:04:56.013501'),(2,'SALE20','限時八折優惠','percent',20,1000,'2026-07-18 16:04:56.011797','2026-08-18 16:04:56.011797',100,1,'2026-07-19 16:04:56.015734'),(3,'test123','test','percent',50,2000,'2026-07-20 09:37:00.000000','2027-07-20 04:00:00.000000',2,1,'2026-07-20 09:38:54.269131');
/*!40000 ALTER TABLE `main_coupon` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_couponusage`
--

DROP TABLE IF EXISTS `main_couponusage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_couponusage` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `discount_amount` int unsigned NOT NULL,
  `used_at` datetime(6) NOT NULL,
  `coupon_id` bigint NOT NULL,
  `user_id` int NOT NULL,
  `order_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_id` (`order_id`),
  KEY `main_couponusage_coupon_id_4a26e551_fk_main_coupon_id` (`coupon_id`),
  KEY `main_couponusage_user_id_e7f0fe3d_fk_auth_user_id` (`user_id`),
  CONSTRAINT `main_couponusage_coupon_id_4a26e551_fk_main_coupon_id` FOREIGN KEY (`coupon_id`) REFERENCES `main_coupon` (`id`),
  CONSTRAINT `main_couponusage_order_id_04c9e654_fk_main_order_id` FOREIGN KEY (`order_id`) REFERENCES `main_order` (`id`),
  CONSTRAINT `main_couponusage_user_id_e7f0fe3d_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `main_couponusage_chk_1` CHECK ((`discount_amount` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_couponusage`
--

LOCK TABLES `main_couponusage` WRITE;
/*!40000 ALTER TABLE `main_couponusage` DISABLE KEYS */;
INSERT INTO `main_couponusage` VALUES (1,100,'2026-07-19 16:04:56.052203',1,4,1),(2,360,'2026-07-19 16:04:56.074728',2,5,3),(3,100,'2026-07-19 16:04:56.098493',1,6,5),(4,100,'2026-07-19 16:47:33.690355',1,6,7),(5,100,'2026-07-19 16:47:34.493506',1,5,8),(7,246,'2026-07-19 17:14:13.278998',2,4,11),(9,100,'2026-07-20 08:19:23.274700',1,4,13),(10,360,'2026-07-20 09:02:05.635418',2,8,15),(11,100,'2026-07-20 09:34:52.549859',1,8,16);
/*!40000 ALTER TABLE `main_couponusage` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_course`
--

DROP TABLE IF EXISTS `main_course`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_course` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `price` int NOT NULL,
  `description` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `image` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `teacher_id` int NOT NULL,
  `is_published` tinyint(1) NOT NULL,
  `level` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `category_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `main_course_teacher_id_f74be8b8_fk_auth_user_id` (`teacher_id`),
  KEY `main_course_category_id_f8b052fb_fk_main_coursecategory_id` (`category_id`),
  CONSTRAINT `main_course_category_id_f8b052fb_fk_main_coursecategory_id` FOREIGN KEY (`category_id`) REFERENCES `main_coursecategory` (`id`),
  CONSTRAINT `main_course_teacher_id_f74be8b8_fk_auth_user_id` FOREIGN KEY (`teacher_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_course`
--

LOCK TABLES `main_course` WRITE;
/*!40000 ALTER TABLE `main_course` DISABLE KEYS */;
INSERT INTO `main_course` VALUES (1,'Python Django 線上課程平台實作',1800,'從 Django 基礎開始，實作會員登入、課程管理、購課流程與 MySQL 資料庫串接。','','2026-07-19 16:04:55.938457',2,1,'intermediate',1),(2,'MySQL 資料庫設計與 ERD 實戰',1500,'學習資料表設計、主外鍵關聯、訂單與優惠券資料庫架構，並建立完整 ERD。','','2026-07-19 16:04:55.941094',2,1,'beginner',1),(3,'Power BI 商業數據分析入門',2000,'使用 Power BI 分析課程平台資料，製作營收、購課、學習時數與優惠券儀表板。','','2026-07-19 16:04:55.943636',3,1,'beginner',3),(4,'UI/UX 介面設計與平台首頁規劃',1200,'學習網站首頁、課程卡片、使用者流程與平台視覺設計，提升系統展示完整度。','','2026-07-19 16:04:55.946119',3,1,'beginner',2),(6,'67大賽',676,'Six Seven!!!!!!!!!!!!!!!!','','2026-07-19 16:50:25.328276',2,1,'advanced',1),(10,'課程分類改進',1234,'輸的人給我跪下','course_images/67-meme-angry-birds-listening.png','2026-07-19 17:07:14.745525',2,1,'advanced',6),(11,'67',111,'111','','2026-07-20 08:17:04.216922',2,1,'intermediate',8),(12,'test video',2000,'測試影片上傳功能','course_images/le-sserafim-2025-3840x2160-21951.jpg','2026-07-20 09:29:44.384537',2,1,'beginner',8),(13,'奶蛙吐舌頭',2000,'123','','2026-07-20 15:35:27.735348',2,1,'advanced',6),(14,'teach',12333,'123','','2026-07-20 16:13:27.463725',2,1,'advanced',9);
/*!40000 ALTER TABLE `main_course` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_courseanswer`
--

DROP TABLE IF EXISTS `main_courseanswer`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_courseanswer` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `content` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `user_id` int NOT NULL,
  `question_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `main_courseanswer_user_id_7ddbaece_fk_auth_user_id` (`user_id`),
  KEY `main_courseanswer_question_id_05fd0189_fk_main_coursequestion_id` (`question_id`),
  CONSTRAINT `main_courseanswer_question_id_05fd0189_fk_main_coursequestion_id` FOREIGN KEY (`question_id`) REFERENCES `main_coursequestion` (`id`),
  CONSTRAINT `main_courseanswer_user_id_7ddbaece_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_courseanswer`
--

LOCK TABLES `main_courseanswer` WRITE;
/*!40000 ALTER TABLE `main_courseanswer` DISABLE KEYS */;
INSERT INTO `main_courseanswer` VALUES (1,'Django 會透過 models.py 定義資料結構，再透過 migration 建立 MySQL 資料表。','2026-07-19 16:04:56.171205',2,1),(2,'老師回覆','2026-07-19 16:47:35.288521',3,2);
/*!40000 ALTER TABLE `main_courseanswer` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_courseaudit`
--

DROP TABLE IF EXISTS `main_courseaudit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_courseaudit` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `comment` longtext COLLATE utf8mb4_unicode_ci,
  `created_at` datetime(6) NOT NULL,
  `reviewed_at` datetime(6) DEFAULT NULL,
  `course_id` bigint NOT NULL,
  `reviewer_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `main_courseaudit_course_id_29ab015b_fk_main_course_id` (`course_id`),
  KEY `main_courseaudit_reviewer_id_6c3ef2dd_fk_auth_user_id` (`reviewer_id`),
  CONSTRAINT `main_courseaudit_course_id_29ab015b_fk_main_course_id` FOREIGN KEY (`course_id`) REFERENCES `main_course` (`id`),
  CONSTRAINT `main_courseaudit_reviewer_id_6c3ef2dd_fk_auth_user_id` FOREIGN KEY (`reviewer_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_courseaudit`
--

LOCK TABLES `main_courseaudit` WRITE;
/*!40000 ALTER TABLE `main_courseaudit` DISABLE KEYS */;
INSERT INTO `main_courseaudit` VALUES (1,'approved','測試資料：課程已審核通過。','2026-07-19 16:04:56.173927','2026-07-19 16:04:56.011797',1,1),(2,'approved','測試資料：課程已審核通過。','2026-07-19 16:04:56.176144','2026-07-19 16:04:56.011797',2,1),(3,'approved','測試資料：課程已審核通過。','2026-07-19 16:04:56.178487','2026-07-19 16:04:56.011797',3,1),(4,'approved','測試資料：課程已審核通過。','2026-07-19 16:04:56.180889','2026-07-19 16:04:56.011797',4,1),(6,'approved','6767','2026-07-19 16:50:25.330484','2026-07-19 16:51:00.000000',6,NULL),(10,'approved','','2026-07-19 17:07:14.747602','2026-07-19 17:07:00.000000',10,7),(11,'approved','','2026-07-20 08:17:04.219126','2026-07-20 08:17:00.000000',11,NULL),(12,'approved','','2026-07-20 09:29:44.387129','2026-07-20 09:33:00.000000',12,NULL),(13,'approved','','2026-07-20 15:35:27.737556',NULL,13,NULL),(14,'approved','','2026-07-20 16:13:27.465249',NULL,14,NULL);
/*!40000 ALTER TABLE `main_courseaudit` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_coursecategory`
--

DROP TABLE IF EXISTS `main_coursecategory`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_coursecategory` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` longtext COLLATE utf8mb4_unicode_ci,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_coursecategory`
--

LOCK TABLES `main_coursecategory` WRITE;
/*!40000 ALTER TABLE `main_coursecategory` DISABLE KEYS */;
INSERT INTO `main_coursecategory` VALUES (1,'程式設計','Python、Django、網頁開發與資料庫相關課程','2026-07-19 16:04:55.931121'),(2,'設計與行銷','UI/UX、品牌設計、社群行銷與內容經營','2026-07-19 16:04:55.933387'),(3,'商業管理','創業、營運、資料分析與商業決策','2026-07-19 16:04:55.935656'),(6,'67冠軍',NULL,'2026-07-19 17:07:14.741285'),(7,'語言學習','','2026-07-19 17:17:10.587645'),(8,'影視製作','','2026-07-19 17:17:32.769219'),(9,'123',NULL,'2026-07-20 16:13:27.461414');
/*!40000 ALTER TABLE `main_coursecategory` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_coursechapter`
--

DROP TABLE IF EXISTS `main_coursechapter`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_coursechapter` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` longtext COLLATE utf8mb4_unicode_ci,
  `sort_order` int unsigned NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `course_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `main_coursechapter_course_id_edfb5c41_fk_main_course_id` (`course_id`),
  CONSTRAINT `main_coursechapter_course_id_edfb5c41_fk_main_course_id` FOREIGN KEY (`course_id`) REFERENCES `main_course` (`id`),
  CONSTRAINT `main_coursechapter_chk_1` CHECK ((`sort_order` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_coursechapter`
--

LOCK TABLES `main_coursechapter` WRITE;
/*!40000 ALTER TABLE `main_coursechapter` DISABLE KEYS */;
INSERT INTO `main_coursechapter` VALUES (1,'第一章：課程導入','介紹課程目標、學習方式與基礎概念。',1,'2026-07-19 16:04:55.949388',1),(2,'第二章：核心實作','進入主要功能實作與案例操作。',2,'2026-07-19 16:04:55.951994',1),(3,'第一章：課程導入','介紹課程目標、學習方式與基礎概念。',1,'2026-07-19 16:04:55.966755',2),(4,'第二章：核心實作','進入主要功能實作與案例操作。',2,'2026-07-19 16:04:55.969692',2),(5,'第一章：課程導入','介紹課程目標、學習方式與基礎概念。',1,'2026-07-19 16:04:55.982858',3),(6,'第二章：核心實作','進入主要功能實作與案例操作。',2,'2026-07-19 16:04:55.985418',3),(7,'第一章：課程導入','介紹課程目標、學習方式與基礎概念。',1,'2026-07-19 16:04:55.998024',4),(8,'第二章：核心實作','進入主要功能實作與案例操作。',2,'2026-07-19 16:04:56.000349',4),(10,'第一章測試','',1,'2026-07-20 09:31:52.116989',12),(11,'2','222',1,'2026-07-20 15:32:40.010359',12),(12,'123','123',1,'2026-07-20 15:36:57.114936',13),(13,'1','123',1,'2026-07-20 16:14:22.698935',14);
/*!40000 ALTER TABLE `main_coursechapter` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_courselesson`
--

DROP TABLE IF EXISTS `main_courselesson`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_courselesson` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` longtext COLLATE utf8mb4_unicode_ci,
  `video_url` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `duration_minutes` int unsigned NOT NULL,
  `sort_order` int unsigned NOT NULL,
  `is_free_preview` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `chapter_id` bigint NOT NULL,
  `video_file` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `main_courselesson_chapter_id_54e79e4a_fk_main_coursechapter_id` (`chapter_id`),
  CONSTRAINT `main_courselesson_chapter_id_54e79e4a_fk_main_coursechapter_id` FOREIGN KEY (`chapter_id`) REFERENCES `main_coursechapter` (`id`),
  CONSTRAINT `main_courselesson_chk_1` CHECK ((`duration_minutes` >= 0)),
  CONSTRAINT `main_courselesson_chk_2` CHECK ((`sort_order` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_courselesson`
--

LOCK TABLES `main_courselesson` WRITE;
/*!40000 ALTER TABLE `main_courselesson` DISABLE KEYS */;
INSERT INTO `main_courselesson` VALUES (1,'1-1 課程介紹與學習目標','本單元說明課程內容、平台功能與學習成果。','https://example.com/video/intro',15,1,1,'2026-07-19 16:04:55.954890',1,NULL),(2,'1-2 開發環境與工具介紹','介紹 VS Code、MySQL、Django、Power BI 等工具。','https://example.com/video/setup',20,2,0,'2026-07-19 16:04:55.957628',1,NULL),(3,'2-1 核心功能設計','說明會員、課程、訂單、優惠券與學習紀錄的設計。','https://example.com/video/core',35,1,0,'2026-07-19 16:04:55.960562',2,NULL),(4,'2-2 資料庫與報表分析','說明 MySQL 資料表與 Power BI 報表的串接方式。','https://example.com/video/database',40,2,0,'2026-07-19 16:04:55.963835',2,NULL),(5,'1-1 課程介紹與學習目標','本單元說明課程內容、平台功能與學習成果。','https://example.com/video/intro',15,1,1,'2026-07-19 16:04:55.972072',3,NULL),(6,'1-2 開發環境與工具介紹','介紹 VS Code、MySQL、Django、Power BI 等工具。','https://example.com/video/setup',20,2,0,'2026-07-19 16:04:55.974888',3,NULL),(7,'2-1 核心功能設計','說明會員、課程、訂單、優惠券與學習紀錄的設計。','https://example.com/video/core',35,1,0,'2026-07-19 16:04:55.977289',4,NULL),(8,'2-2 資料庫與報表分析','說明 MySQL 資料表與 Power BI 報表的串接方式。','https://example.com/video/database',40,2,0,'2026-07-19 16:04:55.980368',4,NULL),(9,'1-1 課程介紹與學習目標','本單元說明課程內容、平台功能與學習成果。','https://example.com/video/intro',15,1,1,'2026-07-19 16:04:55.987790',5,NULL),(10,'1-2 開發環境與工具介紹','介紹 VS Code、MySQL、Django、Power BI 等工具。','https://example.com/video/setup',20,2,0,'2026-07-19 16:04:55.990475',5,NULL),(11,'2-1 核心功能設計','說明會員、課程、訂單、優惠券與學習紀錄的設計。','https://example.com/video/core',35,1,0,'2026-07-19 16:04:55.992760',6,NULL),(12,'2-2 資料庫與報表分析','說明 MySQL 資料表與 Power BI 報表的串接方式。','https://example.com/video/database',40,2,0,'2026-07-19 16:04:55.995624',6,NULL),(13,'1-1 課程介紹與學習目標','本單元說明課程內容、平台功能與學習成果。','https://example.com/video/intro',15,1,1,'2026-07-19 16:04:56.002927',7,NULL),(14,'1-2 開發環境與工具介紹','介紹 VS Code、MySQL、Django、Power BI 等工具。','https://example.com/video/setup',20,2,0,'2026-07-19 16:04:56.005151',7,NULL),(15,'2-1 核心功能設計','說明會員、課程、訂單、優惠券與學習紀錄的設計。','https://example.com/video/core',35,1,0,'2026-07-19 16:04:56.007677',8,NULL),(16,'2-2 資料庫與報表分析','說明 MySQL 資料表與 Power BI 報表的串接方式。','https://example.com/video/database',40,2,0,'2026-07-19 16:04:56.009926',8,NULL),(19,'test','',NULL,3,1,1,'2026-07-20 09:32:24.155290',10,'course_videos/videoplayback.mp4');
/*!40000 ALTER TABLE `main_courselesson` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_coursequestion`
--

DROP TABLE IF EXISTS `main_coursequestion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_coursequestion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `course_id` bigint NOT NULL,
  `lesson_id` bigint DEFAULT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `main_coursequestion_course_id_ea87212d_fk_main_course_id` (`course_id`),
  KEY `main_coursequestion_lesson_id_0ec7ce17_fk_main_courselesson_id` (`lesson_id`),
  KEY `main_coursequestion_user_id_ee27a630_fk_auth_user_id` (`user_id`),
  CONSTRAINT `main_coursequestion_course_id_ea87212d_fk_main_course_id` FOREIGN KEY (`course_id`) REFERENCES `main_course` (`id`),
  CONSTRAINT `main_coursequestion_lesson_id_0ec7ce17_fk_main_courselesson_id` FOREIGN KEY (`lesson_id`) REFERENCES `main_courselesson` (`id`),
  CONSTRAINT `main_coursequestion_user_id_ee27a630_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_coursequestion`
--

LOCK TABLES `main_coursequestion` WRITE;
/*!40000 ALTER TABLE `main_coursequestion` DISABLE KEYS */;
INSERT INTO `main_coursequestion` VALUES (1,'Django 和 MySQL 的資料表是怎麼連動的？','我想了解 Django models.py 和 MySQL 資料表之間的關係。','2026-07-19 16:04:56.168697',1,NULL,4),(2,'問題A','內容','2026-07-19 16:47:34.515052',4,NULL,6);
/*!40000 ALTER TABLE `main_coursequestion` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_enrollment`
--

DROP TABLE IF EXISTS `main_enrollment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_enrollment` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `purchased_at` datetime(6) NOT NULL,
  `course_id` bigint NOT NULL,
  `student_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `main_enrollment_student_id_course_id_56345ecf_uniq` (`student_id`,`course_id`),
  KEY `main_enrollment_course_id_2421a12e_fk_main_course_id` (`course_id`),
  CONSTRAINT `main_enrollment_course_id_2421a12e_fk_main_course_id` FOREIGN KEY (`course_id`) REFERENCES `main_course` (`id`),
  CONSTRAINT `main_enrollment_student_id_2270d951_fk_auth_user_id` FOREIGN KEY (`student_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_enrollment`
--

LOCK TABLES `main_enrollment` WRITE;
/*!40000 ALTER TABLE `main_enrollment` DISABLE KEYS */;
INSERT INTO `main_enrollment` VALUES (1,'2026-07-19 16:04:56.055081',1,4),(2,'2026-07-19 16:04:56.065015',3,4),(4,'2026-07-19 16:04:56.087016',2,5),(5,'2026-07-19 16:04:56.101104',4,6),(6,'2026-07-19 16:22:44.228641',2,4),(7,'2026-07-19 16:47:33.687853',1,6),(8,'2026-07-19 16:47:34.489521',3,5),(9,'2026-07-19 16:47:34.501165',4,5),(11,'2026-07-19 17:14:13.277158',10,4),(13,'2026-07-20 08:19:23.272953',6,4),(14,'2026-07-20 08:37:33.788040',11,4),(15,'2026-07-20 09:02:05.629317',1,8),(16,'2026-07-20 09:34:52.547973',12,8),(24,'2026-07-21 15:44:56.803819',1,2);
/*!40000 ALTER TABLE `main_enrollment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_favorite`
--

DROP TABLE IF EXISTS `main_favorite`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_favorite` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `course_id` bigint NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `main_favorite_user_id_course_id_e3d154b8_uniq` (`user_id`,`course_id`),
  KEY `main_favorite_course_id_2b01c06d_fk_main_course_id` (`course_id`),
  CONSTRAINT `main_favorite_course_id_2b01c06d_fk_main_course_id` FOREIGN KEY (`course_id`) REFERENCES `main_course` (`id`),
  CONSTRAINT `main_favorite_user_id_995d93ea_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_favorite`
--

LOCK TABLES `main_favorite` WRITE;
/*!40000 ALTER TABLE `main_favorite` DISABLE KEYS */;
INSERT INTO `main_favorite` VALUES (2,'2026-07-19 16:04:56.147806',3,5),(3,'2026-07-19 16:04:56.150554',1,6),(4,'2026-07-19 16:22:44.202230',2,4),(5,'2026-07-20 16:15:51.245589',10,2);
/*!40000 ALTER TABLE `main_favorite` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_learningrecord`
--

DROP TABLE IF EXISTS `main_learningrecord`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_learningrecord` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `minutes` int unsigned NOT NULL,
  `watched_at` datetime(6) NOT NULL,
  `course_id` bigint NOT NULL,
  `user_id` int NOT NULL,
  `lesson_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `main_learningrecord_course_id_d10b5663_fk_main_course_id` (`course_id`),
  KEY `main_learningrecord_user_id_f69f70a5_fk_auth_user_id` (`user_id`),
  KEY `main_learningrecord_lesson_id_76d52c56_fk_main_courselesson_id` (`lesson_id`),
  CONSTRAINT `main_learningrecord_course_id_d10b5663_fk_main_course_id` FOREIGN KEY (`course_id`) REFERENCES `main_course` (`id`),
  CONSTRAINT `main_learningrecord_lesson_id_76d52c56_fk_main_courselesson_id` FOREIGN KEY (`lesson_id`) REFERENCES `main_courselesson` (`id`),
  CONSTRAINT `main_learningrecord_user_id_f69f70a5_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `main_learningrecord_chk_1` CHECK ((`minutes` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_learningrecord`
--

LOCK TABLES `main_learningrecord` WRITE;
/*!40000 ALTER TABLE `main_learningrecord` DISABLE KEYS */;
INSERT INTO `main_learningrecord` VALUES (3,15,'2026-07-19 16:04:56.115195',3,4,9),(4,20,'2026-07-19 16:04:56.117869',3,4,10),(7,15,'2026-07-19 16:04:56.130514',2,5,5),(8,20,'2026-07-19 16:04:56.133833',2,5,6),(9,15,'2026-07-19 16:04:56.140153',4,6,13),(10,20,'2026-07-19 16:04:56.142692',4,6,14),(11,30,'2026-07-19 16:47:36.106852',1,6,NULL),(23,3,'2026-07-20 15:05:36.121285',12,8,19);
/*!40000 ALTER TABLE `main_learningrecord` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_lessonprogress`
--

DROP TABLE IF EXISTS `main_lessonprogress`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_lessonprogress` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `watched_map` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `watched_seconds` int unsigned NOT NULL,
  `last_position` int unsigned NOT NULL,
  `duration` int unsigned NOT NULL,
  `is_completed` tinyint(1) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `course_id` bigint NOT NULL,
  `lesson_id` bigint NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `main_lessonprogress_user_id_lesson_id_41c5d8e5_uniq` (`user_id`,`lesson_id`),
  KEY `main_lessonprogress_course_id_2b946a66_fk_main_course_id` (`course_id`),
  KEY `main_lessonprogress_lesson_id_9c9a88df_fk_main_courselesson_id` (`lesson_id`),
  CONSTRAINT `main_lessonprogress_course_id_2b946a66_fk_main_course_id` FOREIGN KEY (`course_id`) REFERENCES `main_course` (`id`),
  CONSTRAINT `main_lessonprogress_lesson_id_9c9a88df_fk_main_courselesson_id` FOREIGN KEY (`lesson_id`) REFERENCES `main_courselesson` (`id`),
  CONSTRAINT `main_lessonprogress_user_id_bedf3645_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `main_lessonprogress_chk_1` CHECK ((`watched_seconds` >= 0)),
  CONSTRAINT `main_lessonprogress_chk_2` CHECK ((`last_position` >= 0)),
  CONSTRAINT `main_lessonprogress_chk_3` CHECK ((`duration` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_lessonprogress`
--

LOCK TABLES `main_lessonprogress` WRITE;
/*!40000 ALTER TABLE `main_lessonprogress` DISABLE KEYS */;
/*!40000 ALTER TABLE `main_lessonprogress` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_notification`
--

DROP TABLE IF EXISTS `main_notification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_notification` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_read` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `main_notification_user_id_8efbf76d_fk_auth_user_id` (`user_id`),
  CONSTRAINT `main_notification_user_id_8efbf76d_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_notification`
--

LOCK TABLES `main_notification` WRITE;
/*!40000 ALTER TABLE `main_notification` DISABLE KEYS */;
INSERT INTO `main_notification` VALUES (1,'歡迎加入 Course Platform','你已成功註冊平台，可以開始瀏覽與購買課程。',0,'2026-07-19 16:04:56.160371',4),(2,'歡迎加入 Course Platform','你已成功註冊平台，可以開始瀏覽與購買課程。',0,'2026-07-19 16:04:56.162917',5),(3,'歡迎加入 Course Platform','你已成功註冊平台，可以開始瀏覽與購買課程。',1,'2026-07-19 16:04:56.165163',6),(4,'退款申請已送出','訂單 #1 的退款申請已送出，等待審核。',0,'2026-07-19 16:22:44.215240',4),(5,'購買成功通知','你已成功購買「MySQL 資料庫設計與 ERD 實戰」，實付金額 NT$ 1500。',0,'2026-07-19 16:22:44.231215',4),(6,'課程已送審','你的課程「測試課程AA」已送出審核，通過後才會上架。',0,'2026-07-19 16:47:31.978114',2),(7,'課程審核通過','你的課程「測試課程AA」已通過審核並上架。',0,'2026-07-19 16:47:32.901435',2),(8,'購買成功通知','你已成功購買「Python Django 線上課程平台實作」，實付金額 NT$ 1700。',1,'2026-07-19 16:47:33.694103',6),(9,'購買成功通知','你已成功購買「Power BI 商業數據分析入門」，實付金額 NT$ 1600。',0,'2026-07-19 16:47:34.491053',5),(10,'購買成功通知','你已成功購買「UI/UX 介面設計與平台首頁規劃」，實付金額 NT$ 1020。',0,'2026-07-19 16:47:34.502842',5),(11,'課程有新提問','課程「UI/UX 介面設計與平台首頁規劃」收到新的問題：問題A',0,'2026-07-19 16:47:34.517314',3),(12,'你的提問已被回覆','課程「UI/UX 介面設計與平台首頁規劃」中你的問題「問題A」已有回答。',1,'2026-07-19 16:47:35.291458',6),(13,'退款申請已送出','訂單 #5 的退款申請已送出，等待審核。',1,'2026-07-19 16:47:35.301593',6),(14,'退款已通過','訂單 #5 的退款申請已通過，將退還 NT$ 1100。',1,'2026-07-19 16:47:36.089367',6),(15,'課程已送審','你的課程「67大賽」已送出審核，通過後才會上架。',0,'2026-07-19 16:50:25.332425',2),(16,'課程已送審','你的課程「自訂分類測試課」已送出審核，通過後才會上架。',0,'2026-07-19 17:02:01.297272',2),(17,'課程已送審','你的課程「整合測試A」已送出審核，通過後才會上架。',0,'2026-07-19 17:04:34.220820',2),(18,'課程已送審','你的課程「整合測試B」已送出審核，通過後才會上架。',0,'2026-07-19 17:04:34.234462',2),(19,'課程已送審','你的課程「課程分類改進」已送出審核，通過後才會上架。',0,'2026-07-19 17:07:14.749833',2),(20,'購買成功通知','你已成功購買「MySQL 資料庫設計與 ERD 實戰」，實付金額 NT$ 1200。',0,'2026-07-19 17:12:12.755986',6),(21,'購買成功通知','你已成功購買「課程分類改進」，實付金額 NT$ 988。',0,'2026-07-19 17:14:13.282386',4),(22,'購買成功通知','你已成功購買「UI/UX 介面設計與平台首頁規劃」，實付金額 NT$ 960。',0,'2026-07-20 08:12:49.201164',4),(23,'課程已送審','你的課程「67」已送出審核，通過後才會上架。',0,'2026-07-20 08:17:04.220957',2),(24,'購買成功通知','你已成功購買「67大賽」，實付金額 NT$ 576。',0,'2026-07-20 08:19:23.278206',4),(25,'購買成功通知','你已成功購買「67」，實付金額 NT$ 111。',0,'2026-07-20 08:37:33.789625',4),(26,'購買成功通知','你已成功購買「Python Django 線上課程平台實作」，實付金額 NT$ 1440。',0,'2026-07-20 09:02:05.644714',8),(27,'課程已送審','你的課程「test video」已送出審核，通過後才會上架。',0,'2026-07-20 09:29:44.389406',2),(28,'購買成功通知','你已成功購買「test video」，實付金額 NT$ 1900。',0,'2026-07-20 09:34:52.554087',8),(29,'購買成功通知','你已成功購買「MySQL 資料庫設計與 ERD 實戰」，實付金額 NT$ 1275。',0,'2026-07-20 14:28:59.459158',6),(30,'購買成功通知','你已完成付款並開通課程：UI/UX 介面設計與平台首頁規劃（實付 NT$ 1200）。',0,'2026-07-20 14:58:01.246895',4),(31,'購買成功通知','你已完成付款並開通課程：MySQL 資料庫設計與 ERD 實戰（實付 NT$ 1500）。',0,'2026-07-20 14:58:02.847496',6),(32,'購買成功通知','你已完成付款並開通課程：test video（實付 NT$ 2000）。',0,'2026-07-20 14:58:03.638526',4),(33,'購買成功通知','你已完成付款並開通課程：Power BI 商業數據分析入門、67大賽（實付 NT$ 2276）。',0,'2026-07-20 14:58:35.190365',6),(34,'課程已送審','你的課程「奶蛙吐舌頭」已送出審核，通過後才會上架。',0,'2026-07-20 15:35:27.739412',2),(35,'課程已送審','你的課程「teach」已送出審核，通過後才會上架。',0,'2026-07-20 16:13:27.466864',2),(36,'購買成功通知','你已完成付款並開通課程：UI/UX 介面設計與平台首頁規劃（實付 NT$ 1200）。',0,'2026-07-21 14:50:58.391528',4),(37,'購買成功通知','你已完成付款並開通課程：Python Django 線上課程平台實作（實付 NT$ 1800）。',0,'2026-07-21 15:44:56.807228',2);
/*!40000 ALTER TABLE `main_notification` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_order`
--

DROP TABLE IF EXISTS `main_order`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_order` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `original_price` int unsigned NOT NULL,
  `discount_amount` int unsigned NOT NULL,
  `final_price` int unsigned NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `coupon_id` bigint DEFAULT NULL,
  `course_id` bigint DEFAULT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `main_order_coupon_id_2c6c35d8_fk_main_coupon_id` (`coupon_id`),
  KEY `main_order_user_id_f3a58861_fk_auth_user_id` (`user_id`),
  KEY `main_order_course_id_52d4a429_fk_main_course_id` (`course_id`),
  CONSTRAINT `main_order_coupon_id_2c6c35d8_fk_main_coupon_id` FOREIGN KEY (`coupon_id`) REFERENCES `main_coupon` (`id`),
  CONSTRAINT `main_order_course_id_52d4a429_fk_main_course_id` FOREIGN KEY (`course_id`) REFERENCES `main_course` (`id`),
  CONSTRAINT `main_order_user_id_f3a58861_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `main_order_chk_1` CHECK ((`original_price` >= 0)),
  CONSTRAINT `main_order_chk_2` CHECK ((`discount_amount` >= 0)),
  CONSTRAINT `main_order_chk_3` CHECK ((`final_price` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=34 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_order`
--

LOCK TABLES `main_order` WRITE;
/*!40000 ALTER TABLE `main_order` DISABLE KEYS */;
INSERT INTO `main_order` VALUES (1,1800,100,1700,'paid','2026-07-19 16:04:56.043697',1,1,4),(2,2000,0,2000,'paid','2026-07-19 16:04:56.057934',NULL,3,4),(3,1800,360,1440,'paid','2026-07-19 16:04:56.067809',2,1,5),(4,1500,0,1500,'paid','2026-07-19 16:04:56.079862',NULL,2,5),(5,1200,100,1100,'refunded','2026-07-19 16:04:56.090793',1,4,6),(6,1500,0,1500,'paid','2026-07-19 16:22:44.221211',NULL,2,4),(7,1800,100,1700,'paid','2026-07-19 16:47:33.680026',1,1,6),(8,2000,400,1600,'paid','2026-07-19 16:47:34.484122',1,3,5),(9,1200,180,1020,'paid','2026-07-19 16:47:34.495977',NULL,4,5),(11,1234,246,988,'paid','2026-07-19 17:14:13.270511',2,10,4),(13,676,100,576,'paid','2026-07-20 08:19:23.266464',1,6,4),(14,111,0,111,'paid','2026-07-20 08:37:33.781912',NULL,11,4),(15,1800,360,1440,'paid','2026-07-20 09:02:05.612348',2,1,8),(16,2000,100,1900,'paid','2026-07-20 09:34:52.541286',1,12,8),(24,1234,246,988,'pending','2026-07-20 15:07:07.666939',2,10,8),(25,1234,0,1234,'pending','2026-07-20 15:08:32.954246',NULL,NULL,8),(26,1234,0,1234,'pending','2026-07-20 15:31:12.390206',NULL,10,8),(27,1234,246,988,'pending','2026-07-20 16:07:41.226391',2,10,8),(28,1234,0,1234,'pending','2026-07-20 16:15:57.941177',NULL,10,2),(30,1800,0,1800,'paid','2026-07-21 14:47:13.141503',NULL,1,2),(31,1200,0,1200,'pending','2026-07-21 14:49:17.516321',NULL,4,4),(32,1200,0,1200,'pending','2026-07-21 14:49:32.951897',NULL,4,4);
/*!40000 ALTER TABLE `main_order` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_orderitem`
--

DROP TABLE IF EXISTS `main_orderitem`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_orderitem` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `price` int unsigned NOT NULL,
  `course_id` bigint NOT NULL,
  `order_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `main_orderitem_course_id_ae90c6c6_fk_main_course_id` (`course_id`),
  KEY `main_orderitem_order_id_72ea9725_fk_main_order_id` (`order_id`),
  CONSTRAINT `main_orderitem_course_id_ae90c6c6_fk_main_course_id` FOREIGN KEY (`course_id`) REFERENCES `main_course` (`id`),
  CONSTRAINT `main_orderitem_order_id_72ea9725_fk_main_order_id` FOREIGN KEY (`order_id`) REFERENCES `main_order` (`id`),
  CONSTRAINT `main_orderitem_chk_1` CHECK ((`price` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=35 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_orderitem`
--

LOCK TABLES `main_orderitem` WRITE;
/*!40000 ALTER TABLE `main_orderitem` DISABLE KEYS */;
INSERT INTO `main_orderitem` VALUES (1,1800,1,1),(2,2000,3,2),(3,1800,1,3),(4,1500,2,4),(5,1200,4,5),(6,1500,2,6),(7,1800,1,7),(8,2000,3,8),(9,1200,4,9),(11,1234,10,11),(13,676,6,13),(14,111,11,14),(15,1800,1,15),(16,2000,12,16),(25,1234,10,24),(26,1234,10,25),(27,1234,10,26),(28,1234,10,27),(29,1234,10,28),(31,1800,1,30),(32,1200,4,31),(33,1200,4,32);
/*!40000 ALTER TABLE `main_orderitem` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_payment`
--

DROP TABLE IF EXISTS `main_payment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_payment` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `method` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `amount` int unsigned NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `transaction_no` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `paid_at` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `order_id` bigint NOT NULL,
  `expire_at` datetime(6) DEFAULT NULL,
  `payment_code` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `virtual_account` varchar(30) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `main_payment_order_id_5a0213d0_fk_main_order_id` (`order_id`),
  CONSTRAINT `main_payment_order_id_5a0213d0_fk_main_order_id` FOREIGN KEY (`order_id`) REFERENCES `main_order` (`id`),
  CONSTRAINT `main_payment_chk_1` CHECK ((`amount` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=34 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_payment`
--

LOCK TABLES `main_payment` WRITE;
/*!40000 ALTER TABLE `main_payment` DISABLE KEYS */;
INSERT INTO `main_payment` VALUES (1,'mock',1700,'paid','MOCK-00001','2026-07-19 16:04:56.011797','2026-07-19 16:04:56.048894',1,NULL,NULL,NULL),(2,'mock',2000,'paid','MOCK-00002','2026-07-19 16:04:56.011797','2026-07-19 16:04:56.062755',2,NULL,NULL,NULL),(3,'mock',1440,'paid','MOCK-00003','2026-07-19 16:04:56.011797','2026-07-19 16:04:56.072112',3,NULL,NULL,NULL),(4,'mock',1500,'paid','MOCK-00004','2026-07-19 16:04:56.011797','2026-07-19 16:04:56.084774',4,NULL,NULL,NULL),(5,'mock',1100,'paid','MOCK-00005','2026-07-19 16:04:56.011797','2026-07-19 16:04:56.096098',5,NULL,NULL,NULL),(6,'mock',1500,'paid','MOCK-00006','2026-07-19 16:22:44.221211','2026-07-19 16:22:44.225359',6,NULL,NULL,NULL),(7,'mock',1700,'paid','MOCK-00007','2026-07-19 16:47:33.680026','2026-07-19 16:47:33.684622',7,NULL,NULL,NULL),(8,'mock',1600,'paid','MOCK-00008','2026-07-19 16:47:34.484122','2026-07-19 16:47:34.487450',8,NULL,NULL,NULL),(9,'mock',1020,'paid','MOCK-00009','2026-07-19 16:47:34.495977','2026-07-19 16:47:34.499166',9,NULL,NULL,NULL),(11,'mock',988,'paid','MOCK-00011','2026-07-19 17:14:13.270511','2026-07-19 17:14:13.274483',11,NULL,NULL,NULL),(13,'mock',576,'paid','MOCK-00013','2026-07-20 08:19:23.266464','2026-07-20 08:19:23.270495',13,NULL,NULL,NULL),(14,'mock',111,'paid','MOCK-00014','2026-07-20 08:37:33.781912','2026-07-20 08:37:33.785606',14,NULL,NULL,NULL),(15,'mock',1440,'paid','MOCK-00015','2026-07-20 09:02:05.612348','2026-07-20 09:02:05.623701',15,NULL,NULL,NULL),(16,'mock',1900,'paid','MOCK-00016','2026-07-20 09:34:52.541286','2026-07-20 09:34:52.544909',16,NULL,NULL,NULL),(24,'mock',988,'pending',NULL,NULL,'2026-07-20 15:07:07.670421',24,NULL,NULL,NULL),(25,'mock',1234,'pending',NULL,NULL,'2026-07-20 15:08:32.957760',25,NULL,NULL,NULL),(26,'mock',1234,'pending',NULL,NULL,'2026-07-20 15:31:12.394379',26,NULL,NULL,NULL),(27,'mock',988,'pending',NULL,NULL,'2026-07-20 16:07:41.230263',27,NULL,NULL,NULL),(28,'mock',1234,'pending',NULL,NULL,'2026-07-20 16:15:57.944744',28,NULL,NULL,NULL),(30,'credit_card',1800,'paid','CARD20260721880253','2026-07-21 15:44:56.796496','2026-07-21 14:47:13.145353',30,NULL,NULL,NULL),(31,'cvs',1200,'pending','CVS20260721266012',NULL,'2026-07-21 14:49:17.519702',31,'2026-07-28 14:49:17.623680','72550200148894','01458787040943'),(32,'mock',1200,'pending',NULL,NULL,'2026-07-21 14:49:32.955051',32,NULL,NULL,NULL);
/*!40000 ALTER TABLE `main_payment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_profile`
--

DROP TABLE IF EXISTS `main_profile`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_profile` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `role` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` int NOT NULL,
  `avatar` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `main_profile_user_id_b40d720a_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_profile`
--

LOCK TABLES `main_profile` WRITE;
/*!40000 ALTER TABLE `main_profile` DISABLE KEYS */;
INSERT INTO `main_profile` VALUES (1,'teacher',2,NULL),(2,'teacher',3,NULL),(3,'student',4,''),(4,'student',5,NULL),(5,'student',6,NULL),(6,'student',8,'avatars/221216-im-lesserafim-twitter-update-with-kim-chaewon-v0-abbu3820i66a1.jpg'),(7,'teacher',9,NULL);
/*!40000 ALTER TABLE `main_profile` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_promotion`
--

DROP TABLE IF EXISTS `main_promotion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_promotion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` longtext COLLATE utf8mb4_unicode_ci,
  `discount_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `discount_value` int unsigned NOT NULL,
  `start_date` datetime(6) NOT NULL,
  `end_date` datetime(6) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `main_promotion_chk_1` CHECK ((`discount_value` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_promotion`
--

LOCK TABLES `main_promotion` WRITE;
/*!40000 ALTER TABLE `main_promotion` DISABLE KEYS */;
INSERT INTO `main_promotion` VALUES (1,'期末專題優惠活動','為專題展示建立的測試促銷活動。','percent',15,'2026-07-18 16:04:56.011797','2026-08-18 16:04:56.011797',1,'2026-07-19 16:04:56.019262');
/*!40000 ALTER TABLE `main_promotion` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_promotion_courses`
--

DROP TABLE IF EXISTS `main_promotion_courses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_promotion_courses` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `promotion_id` bigint NOT NULL,
  `course_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `main_promotion_courses_promotion_id_course_id_75a7739c_uniq` (`promotion_id`,`course_id`),
  KEY `main_promotion_courses_course_id_69c18bfe_fk_main_course_id` (`course_id`),
  CONSTRAINT `main_promotion_cours_promotion_id_cdfb9f83_fk_main_prom` FOREIGN KEY (`promotion_id`) REFERENCES `main_promotion` (`id`),
  CONSTRAINT `main_promotion_courses_course_id_69c18bfe_fk_main_course_id` FOREIGN KEY (`course_id`) REFERENCES `main_course` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_promotion_courses`
--

LOCK TABLES `main_promotion_courses` WRITE;
/*!40000 ALTER TABLE `main_promotion_courses` DISABLE KEYS */;
INSERT INTO `main_promotion_courses` VALUES (1,1,1),(2,1,2),(3,1,3),(4,1,4);
/*!40000 ALTER TABLE `main_promotion_courses` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_refund`
--

DROP TABLE IF EXISTS `main_refund`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_refund` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `amount` int unsigned NOT NULL,
  `reason` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `processed_at` datetime(6) DEFAULT NULL,
  `order_id` bigint NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `main_refund_order_id_bdcf5e0f_fk_main_order_id` (`order_id`),
  KEY `main_refund_user_id_05477b4a_fk_auth_user_id` (`user_id`),
  CONSTRAINT `main_refund_order_id_bdcf5e0f_fk_main_order_id` FOREIGN KEY (`order_id`) REFERENCES `main_order` (`id`),
  CONSTRAINT `main_refund_user_id_05477b4a_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `main_refund_chk_1` CHECK ((`amount` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_refund`
--

LOCK TABLES `main_refund` WRITE;
/*!40000 ALTER TABLE `main_refund` DISABLE KEYS */;
INSERT INTO `main_refund` VALUES (1,1700,'測試退款','pending','2026-07-19 16:22:44.213491',NULL,1,4),(2,1100,'測試','approved','2026-07-19 16:47:35.300012','2026-07-19 16:47:36.085171',5,6);
/*!40000 ALTER TABLE `main_refund` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_review`
--

DROP TABLE IF EXISTS `main_review`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_review` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `rating` smallint unsigned NOT NULL,
  `comment` longtext COLLATE utf8mb4_unicode_ci,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `course_id` bigint NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `main_review_user_id_course_id_f20306be_uniq` (`user_id`,`course_id`),
  KEY `main_review_course_id_f8fd0c84_fk_main_course_id` (`course_id`),
  CONSTRAINT `main_review_course_id_f8fd0c84_fk_main_course_id` FOREIGN KEY (`course_id`) REFERENCES `main_course` (`id`),
  CONSTRAINT `main_review_user_id_ee71ed52_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `main_review_chk_1` CHECK ((`rating` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_review`
--

LOCK TABLES `main_review` WRITE;
/*!40000 ALTER TABLE `main_review` DISABLE KEYS */;
INSERT INTO `main_review` VALUES (1,5,'課程內容完整，對專題實作很有幫助。','2026-07-19 16:04:56.153228','2026-07-19 16:04:56.153242',1,4),(2,4,'可以快速了解 Django 和資料庫串接。','2026-07-19 16:04:56.155454','2026-07-19 16:04:56.155469',1,5),(3,5,'首頁設計和使用者流程講得很清楚。','2026-07-19 16:04:56.157889','2026-07-19 16:04:56.157904',4,6);
/*!40000 ALTER TABLE `main_review` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `main_usercoupon`
--

DROP TABLE IF EXISTS `main_usercoupon`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `main_usercoupon` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `received_at` datetime(6) NOT NULL,
  `used_at` datetime(6) DEFAULT NULL,
  `coupon_id` bigint NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `main_usercoupon_coupon_id_7b923a61_fk_main_coupon_id` (`coupon_id`),
  KEY `main_usercoupon_user_id_bc7b9e3a_fk_auth_user_id` (`user_id`),
  CONSTRAINT `main_usercoupon_coupon_id_7b923a61_fk_main_coupon_id` FOREIGN KEY (`coupon_id`) REFERENCES `main_coupon` (`id`),
  CONSTRAINT `main_usercoupon_user_id_bc7b9e3a_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `main_usercoupon`
--

LOCK TABLES `main_usercoupon` WRITE;
/*!40000 ALTER TABLE `main_usercoupon` DISABLE KEYS */;
INSERT INTO `main_usercoupon` VALUES (1,'unused','2026-07-19 16:04:56.025171',NULL,1,4),(2,'unused','2026-07-19 16:04:56.027896',NULL,1,5),(3,'unused','2026-07-19 16:04:56.030413',NULL,1,6),(4,'unused','2026-07-19 16:26:13.625953',NULL,2,4),(5,'unused','2026-07-20 09:01:45.344271',NULL,2,8),(6,'unused','2026-07-20 09:01:47.515514',NULL,1,8),(8,'unused','2026-07-20 15:08:22.662164',NULL,3,8),(9,'unused','2026-07-20 15:48:42.074088',NULL,3,2);
/*!40000 ALTER TABLE `main_usercoupon` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-07-22  0:30:17
