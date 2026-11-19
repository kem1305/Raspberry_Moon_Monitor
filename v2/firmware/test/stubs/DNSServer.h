#pragma once
#include <WiFi.h>
enum class DNSReplyCode { NoError = 0 };
struct DNSServer { void setErrorReplyCode(DNSReplyCode) {} void start(int, const char*, IPAddress) {} void processNextRequest() {} };
