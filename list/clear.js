//const remoteUrl = "https://raw.githubusercontent.com/W-Webber/jd_surge/refs/heads/feature-qx/config_helper.js";
const remoteUrl = "https://raw.githubusercontent.com/W-Webber/Clash/refs/heads/master/list/remote_test.js"

const $argument = "clear";

(async () => {
  try {
    const resp = await $task.fetch({ url: remoteUrl });
    console.log("============ begin ===========");
    eval(resp.body);  // 远程脚本中可以直接用 REMOTE_ARG 这个变量
    console.log("============ end  ===========");
    //console.log(resp.body);
    //$done();
  } catch (e) {
    $notify("远程脚本加载失败", "", String(e));
    $done();
  }
})();